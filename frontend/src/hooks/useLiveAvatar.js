import { useCallback, useEffect, useRef, useState } from "react";
import { createAndStartLiveAvatarSession } from "../services/liveAvatarService.js";
import { extractApiError } from "../utils/apiErrors.js";

/**
 * Manages the opt-in HeyGen LiveAvatar WebRTC session lifecycle.
 * - Never auto-connects on mount (prevents burning paid streaming minutes on page load).
 * - Connects only when connectAvatar() is explicitly triggered by the candidate.
 * - Cleans up and disconnects the WebRTC session on interview completion or unmount.
 */
export function useLiveAvatar({ sessionId, isSessionCompleted = false }) {
  const videoRef = useRef(null);
  const clientRef = useRef(null);

  const [connectionState, setConnectionState] = useState("standby"); // standby | connecting | connected | unavailable | error
  const [isAvatarSpeaking, setIsAvatarSpeaking] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");

  const disconnectAvatar = useCallback(async () => {
    const active = clientRef.current;
    clientRef.current = null;
    setIsAvatarSpeaking(false);

    if (active) {
      try {
        await active.stop();
      } catch {
        // Ignore teardown errors
      }
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setConnectionState("standby");
  }, []);

  const connectAvatar = useCallback(async () => {
    if (
      !sessionId ||
      isSessionCompleted ||
      connectionState === "connecting" ||
      connectionState === "connected"
    ) {
      return false;
    }

    setConnectionState("connecting");
    setStatusMessage("");

    try {
      const client = await createAndStartLiveAvatarSession({
        sessionId,
        videoElement: videoRef.current,
        onSpeakingChange: (speaking) => setIsAvatarSpeaking(Boolean(speaking)),
        onDisconnected: () => {
          clientRef.current = null;
          setIsAvatarSpeaking(false);
          setConnectionState("standby");
        },
      });

      clientRef.current = client;
      setConnectionState("connected");
      return true;
    } catch (error) {
      clientRef.current = null;
      setIsAvatarSpeaking(false);

      const httpStatus = error?.response?.status;
      if (
        error?.code === "SDK_NOT_INSTALLED" ||
        httpStatus === 404 ||
        httpStatus === 501 ||
        httpStatus === 503
      ) {
        setConnectionState("unavailable");
        setStatusMessage(
          "Live video avatar is not configured on this server (missing LIVEAVATAR_API_KEY or token endpoint). Continuing with built-in voice narration."
        );
      } else {
        const parsed = extractApiError(
          error,
          "Could not connect to the live video interviewer. Continuing with built-in voice narration."
        );
        setConnectionState("error");
        setStatusMessage(parsed.message);
      }
      return false;
    }
  }, [connectionState, isSessionCompleted, sessionId]);

  const speakWithAvatar = useCallback(async (questionText) => {
    const active = clientRef.current;
    if (!active) return false;
    try {
      return await active.speakQuestion(questionText);
    } catch {
      setIsAvatarSpeaking(false);
      return false;
    }
  }, []);

  const interruptAvatar = useCallback(async () => {
    const active = clientRef.current;
    if (!active) return;
    try {
      await active.interrupt();
    } catch {
      // Ignore interrupt errors
    } finally {
      setIsAvatarSpeaking(false);
    }
  }, []);

  useEffect(() => {
    if (isSessionCompleted && clientRef.current) {
      disconnectAvatar();
    }
  }, [isSessionCompleted, disconnectAvatar]);

  useEffect(() => {
    return () => {
      const active = clientRef.current;
      clientRef.current = null;
      if (active) {
        try {
          active.stop();
        } catch {
          // Ignore unmount stop errors
        }
      }
    };
  }, []);

  return {
    videoRef,
    connectionState,
    isConnected: connectionState === "connected",
    isAvatarSpeaking,
    statusMessage,
    connectAvatar,
    disconnectAvatar,
    speakWithAvatar,
    interruptAvatar,
  };
}

