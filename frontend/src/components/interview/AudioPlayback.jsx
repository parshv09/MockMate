import { FileAudio, RotateCcw } from "lucide-react";
import { formatRecordingDuration } from "../../hooks/useAudioRecorder.js";
import { formatFileSize } from "../../utils/resumeValidation.js";
import { Button } from "../ui/Button.jsx";

export function AudioPlayback({
  audioUrl,
  audioBlob,
  audioFilename = "candidate-answer.webm",
  durationSeconds = 0,
  disabled = false,
  onDiscard,
}) {
  if (!audioBlob && !audioUrl) return null;

  const sizeLabel = audioBlob?.size ? formatFileSize(audioBlob.size) : "";

  return (
    <div
      aria-label="Recorded answer playback"
      className="space-y-3 rounded-xl border border-teal-600/25 bg-secondary-subtle/50 p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-white">
            <FileAudio className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">
              {audioFilename}
            </p>
            <p className="font-mono text-xs text-slate-600 tabular-nums">
              {durationSeconds > 0
                ? `Duration ${formatRecordingDuration(durationSeconds)}`
                : "Audio ready"}
              {sizeLabel ? ` · ${sizeLabel}` : ""}
            </p>
          </div>
        </div>

        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={disabled}
          onClick={onDiscard}
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Re-record</span>
        </Button>
      </div>

      {audioUrl ? (
        <audio
          controls
          src={audioUrl}
          aria-label="Preview recorded voice answer"
          className="h-10 w-full"
        />
      ) : null}
    </div>
  );
}

