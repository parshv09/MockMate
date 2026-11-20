import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, Mic, Video, VideoOff } from "lucide-react";
import {
  MAX_VIDEO_FRAME_BYTES,
  uploadVideoFrame,
} from "../../api/video.api.js";
import { formatRecordingDuration } from "../../hooks/useAudioRecorder.js";

const FRAME_CAPTURE_INTERVAL_MS = 4000;

/**
 * Compact Picture-in-Picture (PiP) candidate camera tile anchored in the
 * bottom-right corner of the video stage. Collapses into a slim pill when the
 * camera is off so it never obscures the interviewer video.
 */
export function CandidatePreview({
  sessionId,
  isSessionCompleted = false,
  recordingState = "idle",
  recordingDuration = 0,
}) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const frameInFlightRef = useRef(false);
  const frameCounterRef = useRef(0);

  const [isEnabled, setIsEnabled] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [telemetry, setTelemetry] = useState(null);

  const stopCamera = useCallback(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // Ignore track stop errors
        }
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    frameInFlightRef.current = false;
    setIsEnabled(false);
    setIsStarting(false);
  }, []);

  const captureAndSendFrame = useCallback(async () => {
    if (
      !sessionId ||
      isSessionCompleted ||
      frameInFlightRef.current ||
      !videoRef.current ||
      !streamRef.current
    ) {
      return;
    }

    const videoEl = videoRef.current;
    const width = videoEl.videoWidth || 320;
    const height = videoEl.videoHeight || 240;

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext?.("2d");
    if (!ctx) return;

    try {
      ctx.drawImage(videoEl, 0, 0, width, height);
    } catch {
      return;
    }

    const blob = await new Promise((resolve) => {
      if (typeof canvas.toBlob === "function") {
        canvas.toBlob(resolve, "image/jpeg", 0.75);
      } else {
        resolve(null);
      }
    });

    if (!blob || blob.size <= 0 || blob.size > MAX_VIDEO_FRAME_BYTES) {
      return;
    }

    frameInFlightRef.current = true;
    frameCounterRef.current += 1;
    const frameId = `s${sessionId}-f${frameCounterRef.current}-${Date.now()}`;

    try {
      const data = await uploadVideoFrame(sessionId, blob, frameId);
      if (data?.status === "ok") {
        setTelemetry({
          faces: data.faces ?? 0,
          eyeContact: Boolean(data.eye_contact),
        });
      }
    } catch {
      // Non-fatal
    } finally {
      frameInFlightRef.current = false;
    }
  }, [sessionId, isSessionCompleted]);

  async function handleEnableCamera() {
    if (isStarting || isEnabled || isSessionCompleted) return;
    setCameraError("");

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("Camera access is not supported in this browser.");
      return;
    }

    setIsStarting(true);

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false,
      });

      streamRef.current = mediaStream;
      setIsEnabled(true);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }

      intervalRef.current = window.setInterval(() => {
        captureAndSendFrame();
      }, FRAME_CAPTURE_INTERVAL_MS);
    } catch (err) {
      const isDenied =
        err?.name === "NotAllowedError" || err?.name === "PermissionDeniedError";
      setCameraError(
        isDenied
          ? "Camera permission was denied."
          : "Unable to access your camera."
      );
      stopCamera();
    } finally {
      setIsStarting(false);
    }
  }

  useEffect(() => {
    if (isEnabled && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [isEnabled]);

  useEffect(() => {
    if (isSessionCompleted && isEnabled) {
      stopCamera();
    }
  }, [isSessionCompleted, isEnabled, stopCamera]);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  const isMicRecording = recordingState === "recording";

  // When camera is off, show a compact unobtrusive pill in the corner so the avatar video is 100% clear
  if (!isEnabled) {
    return (
      <div
        aria-label="Candidate camera preview"
        className="flex flex-col items-end gap-1.5"
      >
        <div className="flex items-center gap-2 rounded-full border border-white/20 bg-[#070D19]/85 px-3 py-1.5 text-xs text-white shadow-lg backdrop-blur-md">
          {isMicRecording ? (
            <span className="inline-flex items-center gap-1 font-mono text-[11px] font-semibold text-rose-300 tabular-nums">
              <Mic className="h-3 w-3 animate-pulse" aria-hidden="true" />
              {formatRecordingDuration(recordingDuration)}
            </span>
          ) : null}

          <button
            type="button"
            disabled={isStarting || isSessionCompleted}
            onClick={handleEnableCamera}
            className="inline-flex items-center gap-1.5 font-medium text-slate-200 transition-colors hover:text-white disabled:opacity-50"
          >
            <Video className="h-3.5 w-3.5 text-teal-300" aria-hidden="true" />
            <span>{isStarting ? "Starting..." : "Enable Camera"}</span>
          </button>
        </div>

        {cameraError ? (
          <div
            role="alert"
            className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-950/90 px-2.5 py-1 text-[11px] text-rose-200 shadow-md"
          >
            <AlertCircle className="h-3 w-3 shrink-0 text-rose-400" aria-hidden="true" />
            <span>{cameraError}</span>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div
      aria-label="Candidate camera preview"
      className="w-36 overflow-hidden rounded-xl border border-white/25 bg-[#070D19]/90 text-white shadow-xl backdrop-blur-md sm:w-44"
    >
      <div className="relative aspect-video w-full bg-slate-950">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          aria-label="Live webcam preview"
          className="h-full w-full object-cover"
        />

        <div className="absolute left-2 top-1.5 flex items-center gap-1.5 rounded-full bg-black/65 px-2 py-0.5 text-[10px] font-medium text-white">
          <span>You</span>
          {isMicRecording ? (
            <span className="inline-flex items-center gap-1 text-rose-300">
              <Mic className="h-2.5 w-2.5" aria-hidden="true" />
              <span className="font-mono tabular-nums">
                {formatRecordingDuration(recordingDuration)}
              </span>
            </span>
          ) : null}
        </div>

        {telemetry ? (
          <div className="absolute bottom-1.5 left-2 rounded bg-black/65 px-1.5 py-0.5 font-mono text-[10px] text-teal-300">
            {telemetry.faces === 1
              ? telemetry.eyeContact
                ? "Eye contact OK"
                : "Face detected"
              : telemetry.faces > 1
              ? "Multiple faces"
              : "No face"}
          </div>
        ) : null}
      </div>

      <div className="border-t border-white/10 px-2 py-1">
        <button
          type="button"
          onClick={stopCamera}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-md bg-white/10 px-2 py-1 text-[11px] font-medium text-slate-200 transition-colors hover:bg-white/20 hover:text-white"
        >
          <VideoOff className="h-3 w-3" aria-hidden="true" />
          <span>Disable Camera</span>
        </button>
      </div>
    </div>
  );
}
