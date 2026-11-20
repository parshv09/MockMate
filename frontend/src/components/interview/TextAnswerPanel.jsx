import { useId, useRef } from "react";
import { FileAudio, Upload, X } from "lucide-react";

/**
 * Text-only answer composer inside the unified bottom AnswerDock.
 * Never displayed simultaneously with VoiceAnswerPanel.
 */
export function TextAnswerPanel({
  answerText = "",
  onAnswerTextChange,
  audioFile = null,
  onAudioFileChange,
  onClearError,
  disabled = false,
}) {
  const textareaId = useId();
  const audioInputRef = useRef(null);

  function handleAudioInput(event) {
    const selected = event.target.files?.[0];
    event.target.value = "";
    if (!selected) return;
    onAudioFileChange?.(selected);
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label
          htmlFor={textareaId}
          className="sr-only"
        >
          Your Answer
        </label>
        <textarea
          id={textareaId}
          name="answer_text"
          rows={4}
          value={answerText}
          onChange={(e) => {
            onAnswerTextChange?.(e.target.value);
            onClearError?.();
          }}
          disabled={disabled}
          placeholder="Type your answer — explain the situation, the actions you took, and the result..."
          className="block w-full rounded-xl border border-border-strong bg-surface px-4 py-3 text-sm leading-relaxed text-foreground placeholder:text-foreground-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60"
        />
      </div>

      {/* Compact Audio File Attachment Option */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <input
          ref={audioInputRef}
          type="file"
          accept=".mp3,.wav,.m4a,.ogg,.webm,.flac,.aac,audio/*"
          disabled={disabled}
          onChange={handleAudioInput}
          aria-label="Attach audio answer file"
          className="sr-only"
        />

        {audioFile ? (
          <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
            <FileAudio className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
            <span className="max-w-[220px] truncate">{audioFile.name}</span>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onAudioFileChange?.(null)}
              aria-label="Remove attached audio file"
              className="rounded p-0.5 text-slate-400 hover:text-slate-700"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            disabled={disabled}
            onClick={() => audioInputRef.current?.click()}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 transition-colors hover:text-slate-800 disabled:opacity-50"
          >
            <Upload className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Attach pre-recorded audio file</span>
          </button>
        )}
      </div>
    </div>
  );
}

