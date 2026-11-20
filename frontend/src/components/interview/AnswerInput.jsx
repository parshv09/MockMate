import { useId, useRef } from "react";
import { AlertCircle, FileAudio, Mic, Type, Upload, X } from "lucide-react";
import { InterviewControls } from "./InterviewControls.jsx";
import { VoiceRecorder } from "./VoiceRecorder.jsx";

export const ALLOWED_AUDIO_EXTENSIONS = [
  ".mp3",
  ".wav",
  ".m4a",
  ".ogg",
  ".webm",
  ".flac",
  ".aac",
];
export const MAX_AUDIO_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB

export function validateAudioFileClient(file) {
  if (!file) return { valid: true, error: "" };

  const name = file.name || "";
  const dotIdx = name.lastIndexOf(".");
  const ext = dotIdx > 0 ? name.slice(dotIdx).toLowerCase() : "";

  if (!ext || !ALLOWED_AUDIO_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      error: `Unsupported audio format${ext ? ` (${ext})` : ""}. Allowed formats: MP3, WAV, M4A, OGG, WEBM, FLAC, AAC.`,
    };
  }

  if (typeof file.size === "number" && file.size > MAX_AUDIO_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: "Audio file size exceeds the 25 MB limit.",
    };
  }

  return { valid: true, error: "" };
}

export function AnswerInput({
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
  const textareaId = useId();
  const audioInputRef = useRef(null);
  const isBusy = isSubmitting || isSkipping || isEnding;
  const isRecordingActive =
    recorder?.recordingState === "recording" ||
    recorder?.recordingState === "paused";

  const wordCount = answerText.trim()
    ? answerText.trim().split(/\s+/).length
    : 0;

  function handleAudioInput(event) {
    const selected = event.target.files?.[0];
    event.target.value = "";
    if (!selected) return;
    onAudioFileChange?.(selected);
  }

  function handleFormSubmit(event) {
    event.preventDefault();
    if (isBusy) return;
    onSubmit?.();
  }

  return (
    <section
      aria-label="Your answer"
      className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-7"
    >
      <form onSubmit={handleFormSubmit} noValidate className="space-y-4">
        {/* Top Row: Answer Mode Tabs & Word/Audio Status */}
        <div className="flex flex-wrap items-center justify-between gap-3">
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
                ? "Voice recording ready"
                : "Microphone mode"
              : `${wordCount} ${wordCount === 1 ? "word" : "words"}`}
          </span>
        </div>

        {error ? (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-xl border border-destructive/25 bg-destructive-bg p-3.5 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : null}

        {/* Voice Recording Panel */}
        {answerMode === "voice" && recorder ? (
          <VoiceRecorder
            recordingState={recorder.recordingState}
            durationSeconds={recorder.durationSeconds}
            audioBlob={recorder.audioBlob}
            audioUrl={recorder.audioUrl}
            audioFilename={recorder.audioFilename}
            audioLevels={recorder.audioLevels}
            recorderError={recorder.recorderError}
            uploadedAudioFile={audioFile}
            onUploadedAudioFileChange={onAudioFileChange}
            onStartRecording={recorder.onStartRecording}
            onPauseRecording={recorder.pauseRecording}
            onResumeRecording={recorder.resumeRecording}
            onStopRecording={recorder.stopRecording}
            onDiscardRecording={recorder.discardRecording}
            disabled={isBusy}
          />
        ) : null}

        {/* Text Answer Box (always mounted or visible in text mode / as supplementary notes in voice mode) */}
        <div className={answerMode === "voice" ? "space-y-1.5 pt-1" : "space-y-1.5"}>
          <label
            htmlFor={textareaId}
            className="block font-display text-sm font-bold text-slate-900"
          >
            {answerMode === "voice"
              ? "Your Answer Notes (optional with voice recording)"
              : "Your Answer"}
          </label>
          <textarea
            id={textareaId}
            name="answer_text"
            rows={answerMode === "voice" ? 3 : 7}
            value={answerText}
            onChange={(e) => {
              onAnswerTextChange?.(e.target.value);
              if (error) onClearError?.();
            }}
            disabled={isBusy}
            placeholder="Structure your answer clearly — explain the context, the actions you took, and the outcome..."
            className="block w-full rounded-xl border border-border-strong bg-surface px-4 py-3 text-sm leading-relaxed text-foreground placeholder:text-foreground-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60"
          />
        </div>

        {/* Optional Audio File Attachment in Text Mode */}
        {answerMode === "text" ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200/80 bg-slate-50/70 px-3.5 py-2.5">
            <input
              ref={audioInputRef}
              type="file"
              accept=".mp3,.wav,.m4a,.ogg,.webm,.flac,.aac,audio/*"
              disabled={isBusy}
              onChange={handleAudioInput}
              aria-label="Attach audio answer file"
              className="sr-only"
            />

            {audioFile ? (
              <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2 text-xs font-medium text-slate-700">
                  <FileAudio className="h-4 w-4 shrink-0 text-secondary" aria-hidden="true" />
                  <span className="truncate">{audioFile.name}</span>
                </div>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => onAudioFileChange?.(null)}
                  aria-label="Remove attached audio file"
                  className="rounded p-1 text-slate-400 hover:bg-slate-200/60 hover:text-slate-700 disabled:opacity-50"
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            ) : (
              <div className="flex w-full flex-wrap items-center justify-between gap-2">
                <span className="text-xs text-slate-500">
                  Prefer to speak? Switch to Voice Answer above or attach an audio file (MP3, WAV, M4A, WEBM up to 25 MB).
                </span>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => audioInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Upload className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Attach Audio</span>
                </button>
              </div>
            )}
          </div>
        ) : null}

        {/* Upload & Processing Progress */}
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
