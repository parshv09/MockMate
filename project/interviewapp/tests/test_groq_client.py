"""
Tests for centralized Groq API key management using open-keypool.
All HTTP calls are mocked; no real Groq API quota is consumed.
"""

import json
import logging
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
import requests
from open_keypool import AllKeysExhaustedError, KeyState

from interviewapp.nlp_utils import evaluate_semantic_correctness
from interviewapp.qgen_groq import generate_learning_roadmap_groq, generate_questions_groq
from interviewapp.services.groq_client import (
    GroqAPIError,
    GroqConfigurationError,
    get_groq_key_pool,
    groq_chat_completion,
    load_groq_api_keys,
    mask_api_key,
    reset_groq_key_pool,
)


def _mock_response(status_code=200, json_data=None, headers=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.text = text or (json.dumps(json_data) if json_data is not None else "")
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


class _MockSDKStatusError(Exception):
    """Simulates a Groq SDK APIStatusError exposing `.status_code` and `.response`."""

    def __init__(self, status_code, headers=None, body=None):
        super().__init__(f"SDK error {status_code}")
        self.status_code = status_code
        self.response = _mock_response(status_code=status_code, json_data=body, headers=headers)


@override_settings(GROQ_API_KEY="", GROQ_MODEL="openai/gpt-oss-20b")
class GroqClientKeyPoolTests(TestCase):
    def setUp(self):
        reset_groq_key_pool()

    def tearDown(self):
        reset_groq_key_pool()

    @patch.dict("os.environ", {"GROQ_API_KEY": "gsk_single_key_123456"}, clear=True)
    @patch("interviewapp.services.groq_client.requests.post")
    def test_single_api_key_success(self, mock_post):
        mock_post.return_value = _mock_response(
            200, {"choices": [{"message": {"content": "hello world"}}]}
        )
        out = groq_chat_completion("ping")
        self.assertEqual(out, "hello world")
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(
            mock_post.call_args.kwargs["headers"]["Authorization"],
            "Bearer gsk_single_key_123456",
        )

    @patch.dict(
        "os.environ",
        {
            "GROQ_API_KEY_3": "gsk_key_three_3333",
            "GROQ_API_KEY_1": "gsk_key_one_1111",
            "GROQ_API_KEY_2": "gsk_key_two_2222",
            "GROQ_API_KEY_4": "gsk_key_four_4444",
        },
        clear=True,
    )
    def test_multiple_indexed_api_keys_loaded_in_order(self):
        keys = load_groq_api_keys()
        self.assertEqual(
            keys,
            [
                "gsk_key_one_1111",
                "gsk_key_two_2222",
                "gsk_key_three_3333",
                "gsk_key_four_4444",
            ],
        )

    @patch.dict(
        "os.environ",
        {
            "GROQ_API_KEY_1": "gsk_rate_limited_1111",
            "GROQ_API_KEY_2": "gsk_healthy_key_2222",
        },
        clear=True,
    )
    @patch("interviewapp.services.groq_client.requests.post")
    def test_primary_key_429_rotates_to_second_key_and_succeeds(self, mock_post):
        r_429 = _mock_response(
            429,
            {"error": {"message": "Rate limit reached"}},
            headers={"Retry-After": "30"},
        )
        r_200 = _mock_response(
            200, {"choices": [{"message": {"content": "ok from key 2"}}]}
        )
        mock_post.side_effect = [r_429, r_200]

        out = groq_chat_completion("test prompt")
        self.assertEqual(out, "ok from key 2")
        self.assertEqual(mock_post.call_count, 2)
        auths = [c.kwargs["headers"]["Authorization"] for c in mock_post.call_args_list]
        self.assertEqual(
            auths,
            ["Bearer gsk_rate_limited_1111", "Bearer gsk_healthy_key_2222"],
        )

    @patch.dict(
        "os.environ",
        {
            "GROQ_API_KEY_1": "gsk_invalid_key_1111",
            "GROQ_API_KEY_2": "gsk_valid_key_2222",
        },
        clear=True,
    )
    @patch("interviewapp.services.groq_client.requests.post")
    def test_invalid_key_401_is_disabled_and_rotates(self, mock_post):
        r_401 = _mock_response(401, {"error": {"message": "Invalid API Key"}})
        r_200 = _mock_response(
            200, {"choices": [{"message": {"content": "ok from valid key"}}]}
        )
        mock_post.side_effect = [r_401, r_200]

        out = groq_chat_completion("test prompt")
        self.assertEqual(out, "ok from valid key")
        pool = get_groq_key_pool()
        states = {r.key: r.state for r in pool._records}
        self.assertEqual(states["gsk_invalid_key_1111"], KeyState.DISABLED)
        self.assertEqual(states["gsk_valid_key_2222"], KeyState.ACTIVE)

    @patch.dict(
        "os.environ",
        {
            "GROQ_API_KEY_1": "gsk_key_one_1111",
            "GROQ_API_KEY_2": "gsk_key_two_2222",
        },
        clear=True,
    )
    @patch("interviewapp.services.groq_client.requests.post")
    def test_transient_5xx_retries_and_succeeds(self, mock_post):
        r_503 = _mock_response(503, {"error": {"message": "Service unavailable"}})
        r_200 = _mock_response(
            200, {"choices": [{"message": {"content": "recovered"}}]}
        )
        mock_post.side_effect = [r_503, r_200]

        out = groq_chat_completion("test 5xx")
        self.assertEqual(out, "recovered")
        self.assertEqual(mock_post.call_count, 2)

    @patch.dict(
        "os.environ",
        {
            "GROQ_API_KEY_1": "gsk_only_key_1111",
            "GROQ_API_KEY_2": "gsk_only_key_2222",
            "GROQ_MAX_RETRIES": "4",
        },
        clear=True,
    )
    @patch("interviewapp.services.groq_client.requests.post")
    def test_all_keys_exhausted_raises_all_keys_exhausted_error(self, mock_post):
        r_429 = _mock_response(
            429,
            {"error": {"message": "Rate limit"}},
            headers={"Retry-After": "60"},
        )
        mock_post.side_effect = [r_429, r_429]

        with self.assertRaises(AllKeysExhaustedError):
            groq_chat_completion("exhaust all")
        self.assertEqual(mock_post.call_count, 2)

    @patch.dict(
        "os.environ",
        {
            "GROQ_API_KEY_1": "gsk_sdk_err_1111",
            "GROQ_API_KEY_2": "gsk_sdk_ok_2222",
        },
        clear=True,
    )
    @patch("interviewapp.services.groq_client.requests.post")
    def test_groq_sdk_style_exception_handled_and_fed_to_pool(self, mock_post):
        sdk_429 = _MockSDKStatusError(
            429,
            headers={"Retry-After": "45"},
            body={"error": {"message": "Too many requests"}},
        )
        r_200 = _mock_response(
            200, {"choices": [{"message": {"content": "after sdk exc"}}]}
        )
        mock_post.side_effect = [sdk_429, r_200]

        out = groq_chat_completion("sdk exc")
        self.assertEqual(out, "after sdk exc")
        pool = get_groq_key_pool()
        states = {r.key: r.state for r in pool._records}
        self.assertEqual(states["gsk_sdk_err_1111"], KeyState.COOLDOWN)
        self.assertEqual(states["gsk_sdk_ok_2222"], KeyState.ACTIVE)

    @patch.dict(
        "os.environ",
        {
            "GROQ_API_KEY_1": "gsk_timeout_1111",
            "GROQ_MAX_RETRIES": "2",
        },
        clear=True,
    )
    @patch("interviewapp.services.groq_client.time.sleep")
    @patch("interviewapp.services.groq_client.requests.post")
    def test_bounded_retries_and_no_nested_retry_explosion(self, mock_post, _mock_sleep):
        mock_post.side_effect = requests.Timeout("timed out")
        with self.assertRaises(requests.Timeout):
            groq_chat_completion("timeout test")
        # Exactly GROQ_MAX_RETRIES=2 calls, no nested retry loops
        self.assertEqual(mock_post.call_count, 2)

    @patch.dict("os.environ", {}, clear=True)
    @patch("interviewapp.services.groq_client._get_setting_or_env", return_value="")
    def test_missing_keys_raises_configuration_error(self, _mock_env):
        with self.assertRaises(GroqConfigurationError):
            groq_chat_completion("no keys")

    @patch.dict(
        "os.environ",
        {
            "GROQ_API_KEY_1": "gsk_secret_alpha_9999",
            "GROQ_API_KEY_2": "gsk_secret_beta_8888",
        },
        clear=True,
    )
    @patch("interviewapp.services.groq_client.requests.post")
    def test_no_api_keys_appear_in_logs_or_errors(self, mock_post):
        mock_post.side_effect = [
            _mock_response(401, {"error": {"message": "bad key"}}),
            _mock_response(401, {"error": {"message": "bad key"}}),
        ]
        with self.assertLogs("interviewapp.services.groq_client", level=logging.INFO) as cm:
            with self.assertRaises(AllKeysExhaustedError) as ctx:
                groq_chat_completion("secret check")

        combined_logs = "\n".join(cm.output)
        self.assertNotIn("gsk_secret_alpha_9999", combined_logs)
        self.assertNotIn("gsk_secret_beta_8888", combined_logs)
        self.assertNotIn("gsk_secret_alpha_9999", str(ctx.exception))
        self.assertNotIn("gsk_secret_beta_8888", str(ctx.exception))
        self.assertEqual(mask_api_key("gsk_secret_alpha_9999"), "gsk_****9999")

    @patch.dict(
        "os.environ",
        {
            "GROQ_API_KEY_1": "gsk_model_fb_1111",
            "GROQ_MODEL": "missing/model-v1",
            "GROQ_FALLBACK_MODELS": "openai/gpt-oss-20b",
        },
        clear=True,
    )
    @patch("interviewapp.services.groq_client.requests.post")
    def test_model_fallback_independent_of_key_rotation(self, mock_post):
        r_404 = _mock_response(404, {"error": {"message": "Model not found"}})
        r_200 = _mock_response(
            200, {"choices": [{"message": {"content": "fallback model ok"}}]}
        )
        mock_post.side_effect = [r_404, r_200]

        out = groq_chat_completion("model fallback")
        self.assertEqual(out, "fallback model ok")
        models_called = [c.kwargs["json"]["model"] for c in mock_post.call_args_list]
        self.assertEqual(models_called, ["missing/model-v1", "openai/gpt-oss-20b"])

    @patch.dict("os.environ", {"GROQ_API_KEY_1": "gsk_e2e_key_1111"}, clear=True)
    @patch("interviewapp.services.groq_client.requests.post")
    def test_roadmap_question_gen_and_evaluation_use_centralized_client(self, mock_post):
        roadmap_json = json.dumps(
            {
                "title": "Backend Plan",
                "overview": "Focus on caching.",
                "estimated_hours": 3,
                "learning_steps": [
                    {
                        "order": 1,
                        "concept": "Caching",
                        "subject": "TECH",
                        "priority": "High",
                        "why_needed": "Score 40%",
                        "learning_objectives": ["Understand TTL"],
                        "how_to_learn": "Practice Redis.",
                        "practical_example": "SET k v EX 60",
                        "exercise": "Build cache.",
                        "interview_questions": ["What is cache stampede?"],
                        "resources": ["Redis Docs"],
                        "expected_outcome": "Explain caching.",
                    }
                ],
            }
        )
        qgen_json = json.dumps(
            [
                {
                    "text": "Explain Redis cache eviction policies.",
                    "keywords": "redis,caching",
                    "difficulty": 3,
                    "type": "reasoning",
                }
            ]
        )
        eval_json = json.dumps({"correctness_score": 55})

        mock_post.side_effect = [
            _mock_response(200, {"choices": [{"message": {"content": roadmap_json}}]}),
            _mock_response(200, {"choices": [{"message": {"content": qgen_json}}]}),
            _mock_response(200, {"choices": [{"message": {"content": eval_json}}]}),
        ]

        roadmap = generate_learning_roadmap_groq(
            {
                "has_sufficient_evidence": True,
                "evidence_status": "sufficient",
                "skill_gaps": [
                    {
                        "concept": "Caching",
                        "subject": "TECH",
                        "priority": "High",
                        "avg_score": 40.0,
                        "demonstrated_weaknesses": ["Average score of 40%."],
                        "improvement_opportunities": ["Review TTL"],
                    }
                ],
            }
        )
        self.assertEqual(roadmap["title"], "Backend Plan")

        questions = generate_questions_groq(role="tech", job_role="Backend", n=1, difficulty=3)
        self.assertEqual(len(questions), 1)

        eval_score = evaluate_semantic_correctness(
            question_text="Explain Redis cache eviction policies.",
            answer_text="LRU evicts least recently used keys.",
            keywords_list=["redis", "caching"],
        )
        self.assertEqual(eval_score, 55)
        self.assertEqual(mock_post.call_count, 3)

