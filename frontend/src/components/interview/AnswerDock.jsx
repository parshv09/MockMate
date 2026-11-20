import { AlertCircle, Mic, Type } from "lucide-react";
import { InterviewControls } from "./InterviewControls.jsx";
import { TextAnswerPanel } from "./TextAnswerPanel.jsx";
import { VoiceAnswerPanel } from "./VoiceAnswerPanel.jsx";

/**
 * Unified bottom control dock grouping mode switching, active answer panel
 * (either VoiceAnswerPanel OR TextAnswerPanel, never both simultaneously),
 * upload progress, and Submit / Skip controls.
 */
export function AnswerDock({
  answerMode = "text", // "text" | "voice"
  onAnswerModeChange,
  answerText = "",
  onAnswerTextChange,
  audioFile = null,
  onAudioFileChange,
  recorder = null,
  error = "",
  onClearError,
  uploadProgress = 0,
  isSubmitting = false,
  isSkipping = false,
  isEnding = false,
  onSubmit,
  onSkip,
}) {
  const isBusy = isSubmitting || isSkipping || isEnding;
  const isRecordingActive =
    recorder?.recordingState === "recording" ||
    recorder?.recordingState === "paused";

  const wordCount = answerText.trim()
    ? answerText.trim().split(/\s+/).length
    : 0;

  function handleFormSubmit(event) {
    event.preventDefault();
    if (isBusy) return;
    onSubmit?.();
  }

  return (
    <section
      aria-label="Answer control dock"
      className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm sm:p-5"
    >
      <form onSubmit={handleFormSubmit} noValidate className="space-y-4">
        {/* Compact Dock Header: Mode Toggle & Status */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div
            role="tablist"
            aria-label="Answer input mode"
            className="inline-flex rounded-xl border border-slate-200 bg-slate-100 p-1"
          >
            <button
              type="button"
              role="tab"
              aria-selected={answerMode === "text"}
              disabled={isBusy || isRecordingActive}
              onClick={() => onAnswerModeChange?.("text")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                answerMode === "text"
                  ? "bg-white text-slate-900 shadow-2xs"
                  : "text-slate-600 hover:text-slate-900"
              } disabled:cursor-not-allowed disabled:opacity-50`}
            >
              <Type className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Text Answer</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={answerMode === "voice"}
              disabled={isBusy}
              onClick={() => onAnswerModeChange?.("voice")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                answerMode === "voice"
                  ? "bg-primary text-white shadow-2xs"
                  : "text-slate-600 hover:text-slate-900"
              } disabled:cursor-not-allowed disabled:opacity-50`}
            >
              <Mic className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Voice Answer</span>
            </button>
          </div>

          <span className="font-mono text-xs text-slate-500 tabular-nums">
            {answerMode === "voice"
              ? recorder?.audioBlob
                ? "Recording ready to submit"
                : "Microphone mode"
              : `${wordCount} ${wordCount === 1 ? "word" : "words"}`}
          </span>
        </div>

        {error ? (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-xl border border-destructive/25 bg-destructive-bg p-3 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : null}

        {/* Exclusive Mode Panel: Voice OR Text (never both at once) */}
        {answerMode === "voice" ? (
          <VoiceAnswerPanel
            recorder={recorder}
            uploadedAudioFile={audioFile}
            onUploadedAudioFileChange={onAudioFileChange}
            disabled={isBusy}
          />
        ) : (
          <TextAnswerPanel
            answerText={answerText}
            onAnswerTextChange={onAnswerTextChange}
            audioFile={audioFile}
            onAudioFileChange={onAudioFileChange}
            onClearError={onClearError}
            disabled={isBusy}
          />
        )}

        {/* Upload & Transcription Progress */}
        {isSubmitting ? (
          <div
            role="status"
            aria-live="polite"
            className="space-y-1.5 rounded-xl border border-primary/20 bg-primary-subtle/50 p-3 text-xs text-slate-700"
          >
            <div className="flex items-center justify-between font-medium">
              <span>
                {recorder?.audioBlob || audioFile
                  ? "Uploading audio & running speech recognition..."
                  : "Evaluating your response..."}
              </span>
              {uploadProgress > 0 ? (
                <span className="font-mono tabular-nums">{uploadProgress}%</span>
              ) : null}
            </div>
            {uploadProgress > 0 ? (
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-150"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            ) : null}
          </div>
        ) : null}

        <InterviewControls
          isSubmitting={isSubmitting}
          isSkipping={isSkipping}
          isEnding={isEnding}
          canSubmit={!isRecordingActive}
          onSkip={onSkip}
        />
      </form>
    </section>
  );
}

