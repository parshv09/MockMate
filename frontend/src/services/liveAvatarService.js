import {
  AgentEventsEnum,
  LiveAvatarSession,
  SessionEvent,
} from "@heygen/liveavatar-web-sdk";
import { apiClient } from "../api/client.js";

/**
 * HeyGen LiveAvatar WebRTC Service Adapter (@heygen/liveavatar-web-sdk).
 *
 * Security & Architecture Contract:
 * - Never reads or stores LIVEAVATAR_API_KEY in the browser.
 * - Requests a short-lived, single-use session token from MockMate's backend:
 *   POST /api/v1/sessions/<sessionId>/avatar/token/
 * - Configures `voiceChat: { defaultMuted: true }` and uses `session.repeat(text)`
 *   so MockMate's backend remains the sole source of interview questions.
 */

export const AVATAR_TOKEN_ENDPOINT = (sessionId) =>
  `/sessions/${sessionId}/avatar/token/`;

let customSessionFactory = null;

/**
 * Allows injecting a mock LiveAvatarSession factory in automated tests.
 */
export function setLiveAvatarSessionFactory(factory) {
  customSessionFactory = typeof factory === "function" ? factory : null;
}

export async function requestLiveAvatarToken(sessionId) {
  const response = await apiClient.post(AVATAR_TOKEN_ENDPOINT(sessionId), {});
  const data = response.data || {};
  const sessionToken = data.session_token || data.sessionToken || data.token;
  if (!sessionToken) {
    throw new Error("Backend did not return a valid LiveAvatar session token.");
  }
  return {
    sessionToken,
    avatarSessionId: data.avatar_session_id || null,
    avatarName: data.avatar_name || data.avatarName || "Sarah",
    provider: data.provider || "heygen_liveavatar",
  };
}

function createSdkSession(token, options) {
  if (customSessionFactory) {
    return customSessionFactory(token, options);
  }
  return new LiveAvatarSession(token, options);
}

export async function createAndStartLiveAvatarSession({
  sessionId,
  videoElement = null,
  onSpeakingChange,
  onDisconnected,
}) {
  const { sessionToken, avatarName, provider } =
    await requestLiveAvatarToken(sessionId);

  const avatarSession = createSdkSession(sessionToken, {
    autoKeepAlive: true,
    voiceChat: { defaultMuted: true },
  });

  const attachToVideo = () => {
    if (videoElement && typeof avatarSession.attach === "function") {
      try {
        avatarSession.attach(videoElement);
        const playPromise = videoElement.play?.();
        if (playPromise && typeof playPromise.catch === "function") {
          playPromise.catch(() => {});
        }
      } catch {
        // Ignore attach errors in non-media test environments
      }
    }
  };

  if (typeof avatarSession.on === "function") {
    avatarSession.on(
      SessionEvent?.SESSION_STREAM_READY || "session.stream_ready",
      () => {
        attachToVideo();
      }
    );
    avatarSession.on(
      AgentEventsEnum?.AVATAR_SPEAK_STARTED || "avatar.speak_started",
      () => {
        onSpeakingChange?.(true);
      }
    );
    avatarSession.on(
      AgentEventsEnum?.AVATAR_SPEAK_ENDED || "avatar.speak_ended",
      () => {
        onSpeakingChange?.(false);
      }
    );
    avatarSession.on(
      SessionEvent?.SESSION_DISCONNECTED || "session.disconnected",
      () => {
        onSpeakingChange?.(false);
        onDisconnected?.();
      }
    );
  }

  await avatarSession.start();
  attachToVideo();

  return {
    avatarName,
    provider,
    async speakQuestion(text) {
      const cleaned = (text || "").trim();
      if (!cleaned) return false;
      onSpeakingChange?.(true);
      try {
        if (typeof avatarSession.repeat === "function") {
          await avatarSession.repeat(cleaned);
        } else if (typeof avatarSession.speak === "function") {
          await avatarSession.speak({ text: cleaned, task_type: "REPEAT" });
        }
        return true;
      } catch (err) {
        onSpeakingChange?.(false);
        throw err;
      }
    },
    async interrupt() {
      onSpeakingChange?.(false);
      if (typeof avatarSession.interrupt === "function") {
        await avatarSession.interrupt();
      }
    },
    async stop() {
      onSpeakingChange?.(false);
      if (typeof avatarSession.stop === "function") {
        await avatarSession.stop();
      }
    },
  };
}
