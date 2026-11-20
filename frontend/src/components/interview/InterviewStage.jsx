import { CandidatePreview } from "./CandidatePreview.jsx";
import { RealisticInterviewer } from "./RealisticInterviewer.jsx";

/**
 * Main virtual interview stage: makes the AI Interviewer the single dominant
 * focal point with a corner Picture-in-Picture candidate preview.
 */
export function InterviewStage({
  session,
  question,
  avatarState = "idle",
  liveAvatar,
  tts,
  recordingState = "idle",
  recordingDuration = 0,
  isCompleted = false,
  isBusy = false,
  onSpeakQuestion,
  onReplayQuestion,
}) {
  const showCaptions = Boolean(
    liveAvatar?.isAvatarSpeaking || (tts?.isSpeaking && !tts?.isPaused)
  );

  return (
    <RealisticInterviewer
      avatarState={avatarState}
      role={question?.role || session?.role || "tech"}
      jobRole={session?.job_role || "Software Engineer"}
      questionText={question?.text || ""}
      showCaptions={showCaptions}
      videoRef={liveAvatar?.videoRef}
      connectionState={liveAvatar?.connectionState}
      statusMessage={liveAvatar?.statusMessage}
      onConnectAvatar={liveAvatar?.connectAvatar}
      onDisconnectAvatar={liveAvatar?.disconnectAvatar}
      isTtsSupported={tts?.isSupported}
      isSpeaking={Boolean(liveAvatar?.isAvatarSpeaking || tts?.isSpeaking)}
      isPaused={Boolean(!liveAvatar?.isConnected && tts?.isPaused)}
      isMuted={Boolean(tts?.isMuted)}
      onSpeakQuestion={onSpeakQuestion}
      onPauseQuestion={
        liveAvatar?.isConnected ? liveAvatar?.interruptAvatar : tts?.pause
      }
      onResumeQuestion={tts?.resume}
      onReplayQuestion={onReplayQuestion}
      onToggleMute={tts?.toggleMute}
      disabled={isBusy}
    >
      <CandidatePreview
        sessionId={session?.id}
        isSessionCompleted={isCompleted}
        recordingState={recordingState}
        recordingDuration={recordingDuration}
      />
    </RealisticInterviewer>
  );
}

