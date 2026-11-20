import {
  Pause,
  Play,
  RotateCcw,
  Volume2,
  VolumeX,
} from "lucide-react";

export function QuestionNarrator({
  questionText = "",
  isSupported = true,
  isSpeaking = false,
  isPaused = false,
  isMuted = false,
  volume = 1,
  voices = [],
  selectedVoiceURI = "",
  onSelectVoice,
  onVolumeChange,
  onSpeak,
  onPause,
  onResume,
  onReplay,
  onToggleMute,
  disabled = false,
}) {
  if (!isSupported) {
    return (
      <div
        role="note"
        className="flex items-center justify-between gap-2 text-xs text-slate-400"
      >
        <span>
          Voice narration is not available in this browser. Question text is shown on screen.
        </span>
      </div>
    );
  }

  function handlePrimaryPlayPause() {
    if (disabled || !questionText) return;
    if (isSpeaking && !isPaused) {
      onPause?.();
    } else if (isPaused) {
      onResume?.();
    } else {
      onSpeak?.(questionText);
    }
  }

  const playPauseLabel =
    isSpeaking && !isPaused
      ? "Pause narration"
      : isPaused
      ? "Resume narration"
      : "Read question aloud";

  return (
    <div
      aria-label="Question narration controls"
      className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-200"
    >
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={disabled || !questionText}
          onClick={handlePrimaryPlayPause}
          aria-label={playPauseLabel}
          className="inline-flex min-h-[34px] items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSpeaking && !isPaused ? (
            <>
              <Pause className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Pause</span>
            </>
          ) : (
            <>
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{isPaused ? "Resume" : "Read Aloud"}</span>
            </>
          )}
        </button>

        <button
          type="button"
          disabled={disabled || !questionText}
          onClick={() => onReplay?.(questionText)}
          aria-label="Repeat question"
          className="inline-flex min-h-[34px] items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Repeat Question</span>
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={onToggleMute}
          aria-pressed={isMuted}
          aria-label={isMuted ? "Unmute interviewer voice" : "Mute interviewer voice"}
          className="inline-flex min-h-[34px] items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-2.5 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-50"
        >
          {isMuted ? (
            <>
              <VolumeX className="h-3.5 w-3.5 text-rose-400" aria-hidden="true" />
              <span>Muted</span>
            </>
          ) : (
            <>
              <Volume2 className="h-3.5 w-3.5 text-teal-300" aria-hidden="true" />
              <span>Voice On</span>
            </>
          )}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5">
          <label htmlFor="narrator-volume" className="text-[11px] text-slate-400">
            Vol
          </label>
          <input
            id="narrator-volume"
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={volume}
            disabled={disabled || isMuted}
            aria-label="Interviewer voice volume"
            onChange={(e) => onVolumeChange?.(Number(e.target.value))}
            className="h-1.5 w-16 cursor-pointer accent-primary"
          />
        </div>

        {voices.length > 1 ? (
          <div>
            <label htmlFor="narrator-voice-select" className="sr-only">
              Select interviewer voice
            </label>
            <select
              id="narrator-voice-select"
              aria-label="Select interviewer voice"
              value={selectedVoiceURI}
              disabled={disabled}
              onChange={(e) => onSelectVoice?.(e.target.value)}
              className="max-w-[150px] truncate rounded-md border border-white/15 bg-[#070D19] px-2 py-1 text-[11px] text-slate-200 focus:border-primary focus:outline-none"
            >
              {voices.map((voice) => (
                <option key={voice.voiceURI} value={voice.voiceURI}>
                  {voice.name} ({voice.lang})
                </option>
              ))}
            </select>
          </div>
        ) : null}
      </div>
    </div>
  );
}

