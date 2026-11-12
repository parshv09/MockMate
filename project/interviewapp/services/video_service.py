import logging
import os
import threading
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.db import transaction, OperationalError

from ..models import InterviewSession
from ..video_utils import count_faces
from ..video_behavior_utils import analyze_eye_contact_and_head
from ..video_summary_utils import compute_video_confidence
from ..video_ai_feedback import generate_video_behavior_feedback

logger = logging.getLogger(__name__)

# In-memory dictionary retained for backward compatibility and test inspection
SESSION_VIDEO_STATS: Dict[str, Dict[str, int]] = defaultdict(
    lambda: {
        "total_frames": 0,
        "face_present_frames": 0,
        "multiple_faces_frames": 0,
        "eye_contact_frames": 0,
        "head_movement_frames": 0,
    }
)

# -----------------------------------------------------------------------------
# Redis Connection Pool & Client Management
# -----------------------------------------------------------------------------
_redis_pool = None
_redis_client_instance = None
_pool_lock = threading.Lock()

# Lua script: Atomic frame increment with finalization guard and frame deduplication
_LUA_INCREMENT_SCRIPT = """
-- KEYS[1]: stats hash key
-- KEYS[2]: frame deduplication set key
-- ARGV[1]: frame_id (or empty string)
-- ARGV[2]: delta_total
-- ARGV[3]: delta_face
-- ARGV[4]: delta_multiple
-- ARGV[5]: delta_eye
-- ARGV[6]: delta_head
-- ARGV[7]: ttl_seconds

local finalized = redis.call('HGET', KEYS[1], 'finalized')
if finalized == '1' then
    return {'err', 'SESSION_FINALIZED'}
end

local frame_id = ARGV[1]
if frame_id ~= '' then
    local is_dup = redis.call('SISMEMBER', KEYS[2], frame_id)
    if is_dup == 1 then
        local raw = redis.call('HGETALL', KEYS[1])
        return {'dup', raw}
    end
    redis.call('SADD', KEYS[2], frame_id)
    redis.call('EXPIRE', KEYS[2], tonumber(ARGV[7]))
end

redis.call('HSETNX', KEYS[1], 'backend', 'redis')
redis.call('HINCRBY', KEYS[1], 'total_frames', tonumber(ARGV[2]))
redis.call('HINCRBY', KEYS[1], 'face_present_frames', tonumber(ARGV[3]))
redis.call('HINCRBY', KEYS[1], 'multiple_faces_frames', tonumber(ARGV[4]))
redis.call('HINCRBY', KEYS[1], 'eye_contact_frames', tonumber(ARGV[5]))
redis.call('HINCRBY', KEYS[1], 'head_movement_frames', tonumber(ARGV[6]))
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[7]))

local raw = redis.call('HGETALL', KEYS[1])
return {'ok', raw}
"""

# Lua script: Atomic finalization marking and retrieval
_LUA_FINALIZE_SCRIPT = """
-- KEYS[1]: stats hash key
-- ARGV[1]: extended_ttl_seconds

local exists = redis.call('EXISTS', KEYS[1])
if exists == 0 then
    return {'not_found'}
end

local already_finalized = redis.call('HGET', KEYS[1], 'finalized')
redis.call('HSET', KEYS[1], 'finalized', '1')
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))

local raw = redis.call('HGETALL', KEYS[1])
if already_finalized == '1' then
    return {'already_finalized', raw}
else
    return {'finalized', raw}
end
"""


def get_redis_client():
    """
    Returns a shared, thread-safe Redis client instance using a reusable connection pool.
    Returns None if Redis is not configured or redis-py is not installed.
    """
    global _redis_pool, _redis_client_instance
    redis_url = getattr(settings, "REDIS_URL", None) or os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None

    try:
        import redis
    except ImportError:
        logger.debug("redis-py is not installed; shared Redis counter unavailable.")
        return None

    if _redis_client_instance is None:
        with _pool_lock:
            if _redis_client_instance is None:
                try:
                    _redis_pool = redis.ConnectionPool.from_url(
                        redis_url,
                        max_connections=20,
                        decode_responses=True,
                        socket_timeout=3.0,
                        socket_connect_timeout=3.0,
                    )
                    client = redis.Redis(connection_pool=_redis_pool)
                    client.ping()
                    _redis_client_instance = client
                except Exception as e:
                    logger.warning("Failed to connect to Redis at %s: %s", redis_url, e)
                    return None

    return _redis_client_instance


def _parse_hgetall(raw_list_or_dict) -> Dict[str, int]:
    """Helper to convert Redis HGETALL results (dict or flat list) into typed integer stats."""
    res = {
        "total_frames": 0,
        "face_present_frames": 0,
        "multiple_faces_frames": 0,
        "eye_contact_frames": 0,
        "head_movement_frames": 0,
    }
    if not raw_list_or_dict:
        return res

    if isinstance(raw_list_or_dict, dict):
        mapping = raw_list_or_dict
    elif isinstance(raw_list_or_dict, (list, tuple)):
        mapping = {}
        for i in range(0, len(raw_list_or_dict), 2):
            if i + 1 < len(raw_list_or_dict):
                mapping[raw_list_or_dict[i]] = raw_list_or_dict[i + 1]
    else:
        return res

    for k in res.keys():
        try:
            res[k] = int(mapping.get(k, 0))
        except (ValueError, TypeError):
            res[k] = 0
    return res


def _normalize_stats(stats: Dict) -> Dict[str, int]:
    """Ensures all 5 metric keys are present in the stats dictionary with default 0."""
    return {
        "total_frames": int(stats.get("total_frames", 0)),
        "face_present_frames": int(stats.get("face_present_frames", 0)),
        "multiple_faces_frames": int(stats.get("multiple_faces_frames", 0)),
        "eye_contact_frames": int(stats.get("eye_contact_frames", 0)),
        "head_movement_frames": int(stats.get("head_movement_frames", 0)),
    }


# -----------------------------------------------------------------------------
# Incremental Shared Counter Logic
# -----------------------------------------------------------------------------
def _increment_video_stats(
    session_id: int,
    deltas: Dict[str, int],
    frame_id: Optional[str] = None
) -> Tuple[Optional[Dict[str, int]], Optional[str]]:
    """
    Applies incremental frame counts to the authoritative storage backend:
    - If Redis is configured, executes atomic Lua script for deduplication, finalization guard, and counter increments.
    - If Redis is not configured, executes serialized atomic database updates on InterviewSession.video_stats_json.
    Returns (stats_dict, error_message).
    """
    str_sid = str(session_id)
    clean_frame_id = (frame_id or "").strip()
    r_client = get_redis_client()

    if r_client is not None:
        stats_key = f"mockmate:video_stats:{str_sid}"
        frames_key = f"mockmate:video_frames:{str_sid}"
        try:
            res = r_client.eval(
                _LUA_INCREMENT_SCRIPT,
                2,
                stats_key,
                frames_key,
                clean_frame_id,
                deltas.get("total_frames", 1),
                deltas.get("face_present_frames", 0),
                deltas.get("multiple_faces_frames", 0),
                deltas.get("eye_contact_frames", 0),
                deltas.get("head_movement_frames", 0),
                86400,  # 24-hour safety TTL
            )
            status = res[0] if res else "err"
            if status == "err":
                err_code = res[1] if len(res) > 1 else "Unknown Redis error"
                if err_code == "SESSION_FINALIZED":
                    return None, "Session is already completed or finalized."
                return None, f"Redis error: {err_code}"

            raw_stats = res[1] if len(res) > 1 else {}
            current_stats = _parse_hgetall(raw_stats)
            SESSION_VIDEO_STATS[str_sid] = dict(current_stats)
            return current_stats, None
        except Exception as e:
            logger.error("Redis error during frame increment for session #%s: %s", session_id, e)
            return None, f"Redis communication error: {str(e)}"

    # -------------------------------------------------------------------------
    # Database-Backed Storage (SQLite / PostgreSQL)
    # Note on SQLite: SQLite uses whole-database write locking; select_for_update()
    # is a no-op in SQLite. Concurrency is handled via the 20s busy timeout and retry loop.
    # -------------------------------------------------------------------------
    max_retries = 5
    current_stats = None
    persisted = False

    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                session = (
                    InterviewSession.objects.select_for_update()
                    .filter(id=session_id)
                    .only("id", "completed", "video_stats_json")
                    .first()
                )
                if not session:
                    return None, "Interview session not found."

                if session.completed:
                    return None, "Session is already completed."

                db_stats = session.video_stats_json or {
                    "total_frames": 0,
                    "face_present_frames": 0,
                    "multiple_faces_frames": 0,
                    "eye_contact_frames": 0,
                    "head_movement_frames": 0,
                }

                # Frame Deduplication in DB backend
                recent_ids = db_stats.get("_recent_frame_ids", [])
                if clean_frame_id and clean_frame_id in recent_ids:
                    # Idempotent return without duplicate increment
                    clean_copy = {k: v for k, v in db_stats.items() if not k.startswith("_")}
                    SESSION_VIDEO_STATS[str_sid] = dict(clean_copy)
                    return clean_copy, None

                for field, amount in deltas.items():
                    db_stats[field] = db_stats.get(field, 0) + amount

                if clean_frame_id:
                    recent_ids.append(clean_frame_id)
                    if len(recent_ids) > 200:
                        recent_ids = recent_ids[-200:]
                    db_stats["_recent_frame_ids"] = recent_ids

                session.video_stats_json = db_stats
                session.save(update_fields=["video_stats_json"])
                current_stats = {k: v for k, v in db_stats.items() if not k.startswith("_")}
                persisted = True
                break
        except OperationalError as oe:
            if attempt == max_retries - 1:
                logger.error(
                    "SQLite lock contention failed after %d retries for session #%s: %s",
                    max_retries, session_id, oe
                )
            time.sleep(0.02 * (2 ** attempt))
        except Exception as exc:
            logger.warning("Error persisting video stats for session #%s: %s", session_id, exc)
            return None, f"Database error: {str(exc)}"

    if not persisted or current_stats is None:
        return None, "Database busy: frame statistics could not be durably persisted."

    SESSION_VIDEO_STATS[str_sid] = dict(current_stats)
    return current_stats, None


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def process_video_frame(
    session_id: int,
    image_bytes: bytes,
    frame_id: Optional[str] = None
) -> Dict:
    """
    Analyzes face presence, eye contact, and head pose for a single video frame,
    updates shared persistent statistics via atomic increments, and returns detection results.
    Guarantees deduplication when frame_id is provided.
    """
    face_count = count_faces(image_bytes)
    behavior = analyze_eye_contact_and_head(image_bytes)

    deltas = {
        "total_frames": 1,
        "face_present_frames": 1 if face_count > 0 else 0,
        "multiple_faces_frames": 1 if face_count > 1 else 0,
        "eye_contact_frames": 1 if behavior.get("eye_contact") else 0,
        "head_movement_frames": 1 if behavior.get("head_movement") else 0,
    }

    stats, err = _increment_video_stats(session_id, deltas, frame_id=frame_id)
    if err is not None:
        return {
            "status": "error",
            "error": err,
            "faces": face_count,
            "eye_contact": behavior.get("eye_contact", False),
            "head_movement": behavior.get("head_movement", False),
        }

    return {
        "status": "ok",
        "faces": face_count,
        "eye_contact": behavior.get("eye_contact", False),
        "head_movement": behavior.get("head_movement", False),
    }


def finalize_session_video_metrics(session: InterviewSession) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Flushes all shared stats to session.video_stats_json, computes aggregate confidence,
    generates AI behavior feedback, persists both, and clears memory/cache for the session.
    Idempotent: Re-invocations return existing computed feedback without re-invoking Groq.
    """
    str_sid = str(session.id)
    session.refresh_from_db(fields=["completed", "video_stats_json", "video_feedback_json"])

    # 1. Idempotency Check: Return existing completed metrics without re-invoking Groq
    if session.completed and session.video_feedback_json is not None:
        raw_map = session.video_stats_json or {}
        clean_stats = _normalize_stats({k: v for k, v in raw_map.items() if not k.startswith("_")})
        video_summary = compute_video_confidence(clean_stats) if clean_stats.get("total_frames", 0) > 0 else None
        return video_summary, session.video_feedback_json

    final_stats = None
    r_client = get_redis_client()

    # 2. Redis Finalization via Atomic Lua Script
    if r_client is not None:
        stats_key = f"mockmate:video_stats:{str_sid}"
        frames_key = f"mockmate:video_frames:{str_sid}"
        try:
            res = r_client.eval(_LUA_FINALIZE_SCRIPT, 1, stats_key, 86400)
            status = res[0] if res else "not_found"
            if status in ("finalized", "already_finalized"):
                raw_stats = res[1] if len(res) > 1 else {}
                final_stats = _parse_hgetall(raw_stats)
            # Remove frame deduplication set to free memory
            r_client.delete(frames_key)
        except Exception as e:
            logger.error("Redis error during finalization for session #%s: %s", session.id, e)

    # 3. Fallback / Recovery from DB if Redis had no data
    if not final_stats:
        db_raw = session.video_stats_json or SESSION_VIDEO_STATS.get(str_sid) or {}
        final_stats = _normalize_stats({k: v for k, v in db_raw.items() if not k.startswith("_")})

    video_summary = None
    video_feedback = session.video_feedback_json

    if final_stats and final_stats.get("total_frames", 0) > 0:
        session.video_stats_json = final_stats
        video_summary = compute_video_confidence(final_stats)

        # 4. Generate AI Behavioral Feedback once (Idempotent)
        if video_feedback is None:
            try:
                video_feedback = generate_video_behavior_feedback(
                    role=session.role,
                    confidence_score=video_summary["confidence_score"],
                    presence_pct=video_summary["presence_pct"],
                    eye_contact_pct=video_summary["eye_contact_pct"],
                    movement_pct=video_summary["movement_pct"],
                )
            except Exception as exc:
                logger.warning("Error generating video behavior AI feedback for session #%s: %s", session.id, exc)
                video_feedback = None

        session.video_feedback_json = video_feedback

        # 5. Durable persistence to Database
        session.save(update_fields=["video_stats_json", "video_feedback_json"])

    # Clean up local memory accumulator
    if str_sid in SESSION_VIDEO_STATS:
        try:
            del SESSION_VIDEO_STATS[str_sid]
        except KeyError:
            pass

    return video_summary, video_feedback
