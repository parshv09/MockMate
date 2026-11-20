import { useRef } from "react";
import {
  AlertCircle,
  Mic,
  Pause,
  Play,
  Square,
  Upload,
} from "lucide-react";
import { Button } from "../ui/Button.jsx";
import { AudioWaveform } from "./AudioWaveform.jsx";
import { AudioPlayback } from "./AudioPlayback.jsx";

export function VoiceRecorder({
  recordingState = "idle", // idle | recording | paused | stopped
  durationSeconds = 0,
  audioBlob = null,
  audioUrl = null,
  audioFilename = "candidate-answer.webm",
  audioLevels = [],
  recorderError = "",
  uploadedAudioFile = null,
  onUploadedAudioFileChange,
  onStartRecording,
  onPauseRecording,
  onResumeRecording,
  onStopRecording,
  onDiscardRecording,
  disabled = false,
}) {
  const fileInputRef = useRef(null);

  const isRecording = recordingState === "recording";
  const isPaused = recordingState === "paused";
  const hasRecordedAudio = recordingState === "stopped" && Boolean(audioBlob);

  function handleFileInputChange(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    onDiscardRecording?.();
    onUploadedAudioFileChange?.(file);
  }

  return (
    <div className="space-y-4" aria-label="Voice answer recorder">
      {recorderError ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-destructive/25 bg-destructive-bg p-3.5 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{recorderError}</span>
        </div>
      ) : null}

      {/* Live Waveform Monitor */}
      <AudioWaveform
        levels={audioLevels}
        recordingState={recordingState}
        durationSeconds={durationSeconds}
      />

      {/* Recording Action Bar */}
      {isRecording || isPaused ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200/80 bg-slate-50 p-3.5">
          <div className="flex flex-wrap items-center gap-2">
            {isRecording ? (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={disabled}
                onClick={onPauseRecording}
              >
                <Pause className="h-4 w-4" aria-hidden="true" />
                <span>Pause Recording</span>
              </Button>
            ) : (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={disabled}
                onClick={onResumeRecording}
              >
                <Play className="h-4 w-4" aria-hidden="true" />
                <span>Resume Recording</span>
              </Button>
            )}
          </div>

          <Button
            type="button"
            variant="destructive"
            size="sm"
            disabled={disabled}
            onClick={onStopRecording}
          >
            <Square className="h-4 w-4" aria-hidden="true" />
            <span>Stop Recording</span>
          </Button>
        </div>
      ) : hasRecordedAudio ? (
        <AudioPlayback
          audioUrl={audioUrl}
          audioBlob={audioBlob}
          audioFilename={audioFilename}
          durationSeconds={durationSeconds}
          disabled={disabled}
          onDiscard={onDiscardRecording}
        />
      ) : uploadedAudioFile ? (
        <AudioPlayback
          audioUrl={null}
          audioBlob={uploadedAudioFile}
          audioFilename={uploadedAudioFile.name}
          durationSeconds={0}
          disabled={disabled}
          onDiscard={() => onUploadedAudioFileChange?.(null)}
        />
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200/80 bg-slate-50/70 p-4">
          <div className="space-y-0.5">
            <p className="text-sm font-semibold text-slate-900">
              Record your voice answer
            </p>
            <p className="text-xs text-slate-500">
              Speak naturally — your audio will be transcribed and evaluated when you submit.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp3,.wav,.m4a,.ogg,.webm,.flac,.aac,audio/*"
              disabled={disabled}
              onChange={handleFileInputChange}
              aria-label="Attach audio answer file"
              className="sr-only"
            />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={disabled}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-4 w-4" aria-hidden="true" />
              <span>Attach Audio</span>
            </Button>

            <Button
              type="button"
              variant="primary"
              size="md"
              disabled={disabled}
              onClick={onStartRecording}
            >
              <Mic className="h-4 w-4" aria-hidden="true" />
              <span>Start Recording</span>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

