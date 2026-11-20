import { VoiceRecorder } from "./VoiceRecorder.jsx";

/**
 * Voice-only answer controls inside the unified bottom AnswerDock.
 * Never displayed simultaneously with TextAnswerPanel.
 */
export function VoiceAnswerPanel({
  recorder,
  uploadedAudioFile = null,
  onUploadedAudioFileChange,
  disabled = false,
}) {
  if (!recorder) return null;

  return (
    <VoiceRecorder
      recordingState={recorder.recordingState}
      durationSeconds={recorder.durationSeconds}
      audioBlob={recorder.audioBlob}
      audioUrl={recorder.audioUrl}
      audioFilename={recorder.audioFilename}
      audioLevels={recorder.audioLevels}
      recorderError={recorder.recorderError}
      uploadedAudioFile={uploadedAudioFile}
      onUploadedAudioFileChange={onUploadedAudioFileChange}
      onStartRecording={recorder.onStartRecording}
      onPauseRecording={recorder.pauseRecording}
      onResumeRecording={recorder.resumeRecording}
      onStopRecording={recorder.stopRecording}
      onDiscardRecording={recorder.discardRecording}
      disabled={disabled}
    />
  );
}

