import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Candidate MIME types mapped to file extensions supported by Django's
 * ALLOWED_AUDIO_EXTENSIONS ({".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac"}).
 */
const CANDIDATE_AUDIO_TYPES = [
  { mimeType: "audio/webm;codecs=opus", extension: ".webm" },
  { mimeType: "audio/webm", extension: ".webm" },
  { mimeType: "audio/ogg;codecs=opus", extension: ".ogg" },
  { mimeType: "audio/mp4", extension: ".m4a" },
  { mimeType: "audio/wav", extension: ".wav" },
];

const DEFAULT_LEVELS = [
  0.18, 0.25, 0.2, 0.3, 0.22, 0.28, 0.2, 0.26, 0.22, 0.3, 0.24, 0.2, 0.28, 0.22, 0.25, 0.18,
];

export function selectSupportedAudioFormat() {
  if (typeof window === "undefined" || typeof window.MediaRecorder === "undefined") {
    return { mimeType: "", extension: ".webm" };
  }

  const isTypeSupported = window.MediaRecorder.isTypeSupported;
  if (typeof isTypeSupported === "function") {
    for (const candidate of CANDIDATE_AUDIO_TYPES) {
      try {
        if (isTypeSupported.call(window.MediaRecorder, candidate.mimeType)) {
          return candidate;
        }
      } catch {
        // Continue checking remaining formats
      }
    }
  }

  return { mimeType: "", extension: ".webm" };
}

export function formatRecordingDuration(totalSeconds = 0) {
  const safe = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

/**
 * Real microphone recording hook using MediaRecorder & Web Audio API.
 * - Never requests microphone permission until startRecording() is explicitly called.
 * - Dynamically selects a backend-compatible MIME type and file extension.
 * - Provides pause, resume, stop, playback URL, and discard/re-record.
 * - Cleans up MediaRecorder, MediaStreamTracks, AudioContext, and Object URLs on unmount.
 */
export function useAudioRecorder() {
  const isSupported =
    typeof window !== "undefined" &&
    Boolean(navigator?.mediaDevices?.getUserMedia) &&
    typeof window.MediaRecorder !== "undefined";

  const [permissionState, setPermissionState] = useState("prompt");
  const [recordingState, setRecordingState] = useState("idle"); // idle | recording | paused | stopped
  const [durationSeconds, setDurationSeconds] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioFilename, setAudioFilename] = useState("candidate-answer.webm");
  const [mimeType, setMimeType] = useState("");
  const [audioLevels, setAudioLevels] = useState(DEFAULT_LEVELS);
  const [recorderError, setRecorderError] = useState("");

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const levelTimerRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const audioUrlRef = useRef(null);

  const revokeCurrentAudioUrl = useCallback(() => {
    if (audioUrlRef.current) {
      try {
        URL.revokeObjectURL(audioUrlRef.current);
      } catch {
        // Ignore URL revoke errors
      }
      audioUrlRef.current = null;
    }
    setAudioUrl(null);
  }, []);

  const stopTracksAndTimers = useCallback(() => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (levelTimerRef.current) {
      window.clearInterval(levelTimerRef.current);
      levelTimerRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch {
        // Ignore close errors
      }
      audioContextRef.current = null;
      analyserRef.current = null;
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
    setAudioLevels(DEFAULT_LEVELS);
  }, []);

  const startLevelMonitor = useCallback((stream) => {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (typeof AudioCtx === "function") {
      try {
        const ctx = new AudioCtx();
        const source = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 64;
        source.connect(analyser);
        audioContextRef.current = ctx;
        analyserRef.current = analyser;
      } catch {
        analyserRef.current = null;
      }
    }

    let tick = 0;
    levelTimerRef.current = window.setInterval(() => {
      tick += 1;
      if (analyserRef.current) {
        const data = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(data);
        const bars = Array.from({ length: 16 }, (_, idx) => {
          const val = data[idx % data.length] || 0;
          return Math.max(0.16, Math.min(1, val / 255));
        });
        setAudioLevels(bars);
      } else {
        // Deterministic wave motion when AudioContext is not available (e.g. jsdom)
        const bars = DEFAULT_LEVELS.map((base, idx) => {
          const offset = Math.sin((tick + idx) * 0.7) * 0.28;
          return Math.max(0.18, Math.min(0.95, base + 0.35 + offset));
        });
        setAudioLevels(bars);
      }
    }, 150);
  }, []);

  const startRecording = useCallback(async () => {
    setRecorderError("");

    if (!navigator?.mediaDevices?.getUserMedia || typeof window.MediaRecorder === "undefined") {
      setPermissionState("error");
      setRecorderError(
        "Microphone recording is not supported in this browser. You can attach an audio file or switch to a text answer."
      );
      return false;
    }

    // Clean up any previous recording first
    revokeCurrentAudioUrl();
    setAudioBlob(null);
    setDurationSeconds(0);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      setPermissionState("granted");

      const chosen = selectSupportedAudioFormat();
      setMimeType(chosen.mimeType);
      const filename = `candidate-answer${chosen.extension}`;
      setAudioFilename(filename);

      const recorder = chosen.mimeType
        ? new window.MediaRecorder(stream, { mimeType: chosen.mimeType })
        : new window.MediaRecorder(stream);

      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event?.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onerror = () => {
        setRecorderError("An error occurred while recording audio. Please try again.");
        stopTracksAndTimers();
        setRecordingState("idle");
      };

      recorder.onstop = () => {
        stopTracksAndTimers();
        const blobType = chosen.mimeType || recorder.mimeType || "audio/webm";
        const assembled = new Blob(chunksRef.current, { type: blobType });

        if (assembled.size <= 0) {
          setRecorderError("No audio was captured. Please check your microphone and try again.");
          setAudioBlob(null);
          setRecordingState("idle");
          return;
        }

        setAudioBlob(assembled);
        if (typeof URL !== "undefined" && typeof URL.createObjectURL === "function") {
          const objectUrl = URL.createObjectURL(assembled);
          audioUrlRef.current = objectUrl;
          setAudioUrl(objectUrl);
        }
        setRecordingState("stopped");
      };

      recorder.start(250);
      setRecordingState("recording");

      timerRef.current = window.setInterval(() => {
        setDurationSeconds((prev) => prev + 1);
      }, 1000);

      startLevelMonitor(stream);
      return true;
    } catch (err) {
      stopTracksAndTimers();
      const isDenied =
        err?.name === "NotAllowedError" || err?.name === "PermissionDeniedError";
      const isMissing =
        err?.name === "NotFoundError" || err?.name === "DevicesNotFoundError";

      setPermissionState(isDenied ? "denied" : "error");
      setRecorderError(
        isDenied
          ? "Microphone permission was denied. Please allow microphone access in your browser settings or use a text answer."
          : isMissing
          ? "No microphone was found on this device. Please connect a microphone or use a text answer."
          : "Could not start microphone recording. Please check your audio device or use a text answer."
      );
      setRecordingState("idle");
      return false;
    }
  }, [revokeCurrentAudioUrl, startLevelMonitor, stopTracksAndTimers]);

  const pauseRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recordingState !== "recording") return;
    try {
      if (typeof recorder.pause === "function" && recorder.state === "recording") {
        recorder.pause();
      }
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setRecordingState("paused");
    } catch {
      // Ignore pause errors
    }
  }, [recordingState]);

  const resumeRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recordingState !== "paused") return;
    try {
      if (typeof recorder.resume === "function" && recorder.state === "paused") {
        recorder.resume();
      }
      timerRef.current = window.setInterval(() => {
        setDurationSeconds((prev) => prev + 1);
      }, 1000);
      setRecordingState("recording");
    } catch {
      // Ignore resume errors
    }
  }, [recordingState]);

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || (recordingState !== "recording" && recordingState !== "paused")) {
      return;
    }
    try {
      if (recorder.state !== "inactive") {
        recorder.stop();
      } else {
        stopTracksAndTimers();
        setRecordingState("stopped");
      }
    } catch {
      stopTracksAndTimers();
      setRecordingState("idle");
    }
  }, [recordingState, stopTracksAndTimers]);

  const discardRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder) {
      try {
        recorder.ondataavailable = null;
        recorder.onstop = null;
        if (recorder.state !== "inactive") {
          recorder.stop();
        }
      } catch {
        // Ignore stop errors
      }
      mediaRecorderRef.current = null;
    }
    stopTracksAndTimers();
    revokeCurrentAudioUrl();
    chunksRef.current = [];
    setAudioBlob(null);
    setDurationSeconds(0);
    setRecorderError("");
    setRecordingState("idle");
  }, [revokeCurrentAudioUrl, stopTracksAndTimers]);

  useEffect(() => {
    return () => {
      const recorder = mediaRecorderRef.current;
      if (recorder) {
        try {
          recorder.ondataavailable = null;
          recorder.onstop = null;
          if (recorder.state !== "inactive") {
            recorder.stop();
          }
        } catch {
          // Ignore
        }
      }
      stopTracksAndTimers();
      revokeCurrentAudioUrl();
    };
  }, [revokeCurrentAudioUrl, stopTracksAndTimers]);

  return {
    isSupported,
    permissionState,
    recordingState,
    durationSeconds,
    audioBlob,
    audioUrl,
    audioFilename,
    mimeType,
    audioLevels,
    recorderError,
    setRecorderError,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    discardRecording,
  };
}
