import {
  Ear,
  Loader2,
  Pause,
  Play,
  Radio,
  RotateCcw,
  Sparkles,
  UserCheck,
  Video,
  VideoOff,
  Volume2,
  VolumeX,
} from "lucide-react";
import { ROLE_LABELS } from "../../utils/dashboardStats.js";

const STATE_CONFIG = {
  speaking: {
    label: "Speaking Question",
    badgeClass: "border-blue-400/40 bg-primary/30 text-blue-100",
    dotClass: "bg-blue-400 animate-pulse",
    icon: Volume2,
  },
  listening: {
    label: "Listening to Candidate",
    badgeClass: "border-teal-400/40 bg-teal-500/25 text-teal-100",
    dotClass: "bg-teal-400 animate-pulse",
    icon: Ear,
  },
  evaluating: {
    label: "Processing Response",
    badgeClass: "border-amber-400/40 bg-amber-500/25 text-amber-100",
    dotClass: "bg-amber-400 animate-pulse",
    icon: Loader2,
  },
  idle: {
    label: "Interviewer Ready",
    badgeClass: "border-white/15 bg-white/10 text-slate-200",
    dotClass: "bg-emerald-400",
    icon: Radio,
  },
};

export function RealisticInterviewer({
  avatarState = "idle", // idle | speaking | listening | evaluating
  role = "tech",
  jobRole = "Software Engineer",
  questionText = "",
  showCaptions = false,
  // LiveAvatar WebRTC props
  videoRef,
  connectionState = "standby", // standby | connecting | connected | unavailable | error
  statusMessage = "",
  onConnectAvatar,
  onDisconnectAvatar,
  // Narration props
  isTtsSupported = true,
  isSpeaking = false,
  isPaused = false,
  isMuted = false,
  onSpeakQuestion,
  onPauseQuestion,
  onResumeQuestion,
  onReplayQuestion,
  onToggleMute,
  disabled = false,
  children = null,
}) {
  const config = STATE_CONFIG[avatarState] || STATE_CONFIG.idle;
  const StatusIcon = config.icon;
  const roleLabel = ROLE_LABELS[role] || "Interview";
  const isConnected = connectionState === "connected";
  const isConnecting = connectionState === "connecting";

  return (
    <section
      aria-label="AI Interviewer Stage"
      data-avatar-state={avatarState}
      className="overflow-hidden rounded-2xl border border-slate-800 bg-[#070D19] text-white shadow-xl"
    >
      {/* Dedicated Top Stage Bar (outside the video canvas so controls NEVER cover the avatar's face) */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 bg-[#0A1324] px-4 py-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2">
            <UserCheck className="h-4 w-4 text-teal-300" aria-hidden="true" />
            <span className="font-display text-xs font-bold text-white sm:text-sm">
              MockMate AI Interviewer
            </span>
            <span className="hidden text-xs text-slate-400 sm:inline">
              · {roleLabel} Lead ({jobRole || "Practice"})
            </span>
          </div>

          <div
            role="status"
            aria-live="polite"
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${config.badgeClass}`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${config.dotClass}`}
              aria-hidden="true"
            />
            <StatusIcon
              className={`h-3 w-3 ${
                avatarState === "evaluating" ? "animate-spin" : ""
              }`}
              aria-hidden="true"
            />
            <span>{config.label}</span>
          </div>
        </div>

        {/* Stage Audio & Video Controls */}
        <div className="flex flex-wrap items-center gap-1.5">
          {isTtsSupported || isConnected ? (
            <>
              <button
                type="button"
                disabled={disabled || !questionText}
                onClick={() => {
                  if (isPaused) {
                    onResumeQuestion?.();
                  } else {
                    onSpeakQuestion?.(questionText);
                  }
                }}
                aria-label="Read question aloud"
                className="inline-flex h-7 items-center gap-1.5 rounded-lg bg-primary px-2.5 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Play className="h-3 w-3" aria-hidden="true" />
                <span>{isPaused ? "Resume" : "Read Aloud"}</span>
              </button>

              {isSpeaking && !isPaused ? (
                <button
                  type="button"
                  disabled={disabled}
                  onClick={onPauseQuestion}
                  aria-label="Pause narration"
                  className="inline-flex h-7 items-center gap-1 rounded-lg border border-white/15 bg-white/10 px-2.5 text-xs font-medium text-white transition-colors hover:bg-white/20 disabled:opacity-50"
                >
                  <Pause className="h-3 w-3" aria-hidden="true" />
                  <span>Pause</span>
                </button>
              ) : null}

              <button
                type="button"
                disabled={disabled || !questionText}
                onClick={() => onReplayQuestion?.(questionText)}
                aria-label="Repeat question"
                className="inline-flex h-7 items-center gap-1 rounded-lg border border-white/15 bg-white/5 px-2.5 text-xs font-medium text-slate-200 transition-colors hover:bg-white/15 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RotateCcw className="h-3 w-3" aria-hidden="true" />
                <span>Repeat</span>
              </button>

              <button
                type="button"
                disabled={disabled}
                onClick={onToggleMute}
                aria-pressed={isMuted}
                aria-label={
                  isMuted ? "Unmute interviewer voice" : "Mute interviewer voice"
                }
                className="inline-flex h-7 items-center justify-center rounded-lg border border-white/15 bg-white/5 px-2 text-xs font-medium text-slate-200 transition-colors hover:bg-white/15 hover:text-white disabled:opacity-50"
              >
                {isMuted ? (
                  <VolumeX className="h-3.5 w-3.5 text-rose-400" aria-hidden="true" />
                ) : (
                  <Volume2 className="h-3.5 w-3.5 text-teal-300" aria-hidden="true" />
                )}
              </button>
            </>
          ) : null}

          {isConnected ? (
            <button
              type="button"
              onClick={onDisconnectAvatar}
              className="inline-flex h-7 items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-2.5 text-xs font-medium text-slate-200 transition-colors hover:bg-rose-500/20 hover:border-rose-400/30 hover:text-rose-200"
            >
              <VideoOff className="h-3 w-3" aria-hidden="true" />
              <span>Disconnect Video</span>
            </button>
          ) : (
            <button
              type="button"
              disabled={isConnecting || disabled}
              onClick={onConnectAvatar}
              className="inline-flex h-7 items-center gap-1.5 rounded-lg border border-teal-400/30 bg-teal-500/15 px-2.5 text-xs font-semibold text-teal-200 transition-colors hover:bg-teal-500/25 disabled:opacity-50"
            >
              <Video className="h-3 w-3" aria-hidden="true" />
              <span>
                {isConnecting ? "Connecting..." : "Connect Live Avatar"}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Unobstructed 16:9 Widescreen Video Viewport */}
      <div className="relative aspect-video w-full bg-gradient-to-b from-[#081020] via-[#0B162C] to-[#0E1C36]">
        {/* Live WebRTC Avatar Video Layer — object-contain preserves full head & shoulders without cropping */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          aria-label="Live AI interviewer video stream"
          className={`h-full w-full object-contain object-top transition-opacity duration-300 ${
            isConnected ? "opacity-100" : "pointer-events-none opacity-0"
          }`}
        />

        {/* Center Standby Backdrop (only when WebRTC video is not connected) */}
        {!isConnected ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
            <div
              className={`flex h-20 w-20 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                avatarState === "speaking"
                  ? "border-blue-400 bg-primary/25 shadow-[0_0_40px_rgba(29,78,216,0.45)]"
                  : avatarState === "listening"
                  ? "border-teal-400 bg-secondary/25 shadow-[0_0_32px_rgba(15,118,110,0.4)]"
                  : "border-white/15 bg-white/5"
              }`}
            >
              <Sparkles
                className={`h-8 w-8 ${
                  avatarState === "speaking"
                    ? "text-blue-300"
                    : avatarState === "listening"
                    ? "text-teal-300"
                    : "text-slate-300"
                }`}
                aria-hidden="true"
              />
            </div>

            <p className="mt-3 font-display text-sm font-semibold text-white">
              {avatarState === "speaking"
                ? "Interviewer is reading the question..."
                : avatarState === "listening"
                ? "Interviewer is listening to your answer..."
                : avatarState === "evaluating"
                ? "Evaluating your answer..."
                : "Virtual Interview Stage"}
            </p>

            {statusMessage ? (
              <p
                role="note"
                className="mt-2 max-w-md rounded-lg border border-white/10 bg-black/45 px-3 py-1.5 text-xs text-slate-300"
              >
                {statusMessage}
              </p>
            ) : (
              <p className="mt-1 max-w-md text-xs text-slate-400">
                Click Connect Live Avatar for real-time video, or use Read Aloud for voice narration.
              </p>
            )}
          </div>
        ) : null}

        {/* Bottom Overlay: Subtitles/Captions (left) + Compact PiP Candidate Preview (bottom-right corner) */}
        <div className="pointer-events-none absolute inset-x-3 bottom-3 z-10 flex items-end justify-between gap-3">
          <div className="pointer-events-auto flex-1">
            {showCaptions && questionText ? (
              <div
                aria-label="Interviewer question captions"
                className="max-w-xl rounded-xl border border-white/15 bg-[#070D19]/85 px-3.5 py-2 text-xs leading-relaxed text-white backdrop-blur-md sm:text-sm"
              >
                <span className="mr-2 rounded bg-primary/40 px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-blue-200">
                  CC
                </span>
                <span>&ldquo;{questionText}&rdquo;</span>
              </div>
            ) : null}
          </div>

          {children ? (
            <div className="pointer-events-auto shrink-0">{children}</div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
