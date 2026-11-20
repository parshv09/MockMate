import { formatRecordingDuration } from "../../hooks/useAudioRecorder.js";

export function AudioWaveform({
  levels = [],
  recordingState = "idle", // idle | recording | paused | stopped
  durationSeconds = 0,
}) {
  const isActive = recordingState === "recording";
  const isPaused = recordingState === "paused";
  const safeLevels =
    Array.isArray(levels) && levels.length > 0
      ? levels
      : [0.2, 0.3, 0.25, 0.4, 0.3, 0.35, 0.25, 0.3, 0.2, 0.35, 0.25, 0.2];

  const statusText = isActive
    ? "Recording live audio"
    : isPaused
    ? "Recording paused"
    : recordingState === "stopped"
    ? "Recording complete"
    : "Microphone ready";

  return (
    <div
      aria-label="Audio waveform monitor"
      className="rounded-xl border border-slate-200/90 bg-slate-900 p-4 text-white"
    >
      <div className="flex items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className={`h-2.5 w-2.5 rounded-full ${
              isActive
                ? "bg-rose-500 animate-pulse"
                : isPaused
                ? "bg-amber-400"
                : "bg-teal-400"
            }`}
          />
          <span className="font-medium text-slate-200">{statusText}</span>
        </div>

        <span
          aria-label="Recording duration"
          className="rounded-md bg-white/10 px-2.5 py-0.5 font-mono text-xs font-bold text-white tabular-nums"
        >
          {formatRecordingDuration(durationSeconds)}
        </span>
      </div>

      <div
        aria-hidden="true"
        className="mt-4 flex h-12 items-center justify-center gap-1.5"
      >
        {safeLevels.map((lvl, idx) => {
          const factor = isActive ? lvl : isPaused ? Math.min(0.35, lvl) : 0.16;
          const pxHeight = Math.max(6, Math.round(factor * 44));
          return (
            <span
              key={idx}
              style={{ height: `${pxHeight}px` }}
              className={`w-1.5 rounded-full transition-all duration-150 ${
                isActive
                  ? "bg-gradient-to-t from-primary to-teal-400"
                  : isPaused
                  ? "bg-amber-400/70"
                  : "bg-slate-700"
              }`}
            />
          );
        })}
      </div>
    </div>
  );
}

