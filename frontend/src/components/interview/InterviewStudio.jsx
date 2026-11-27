import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FileBarChart,
  RefreshCw,
} from "lucide-react";
import { useAudioRecorder } from "../../hooks/useAudioRecorder.js";
import { useInterviewSession } from "../../hooks/useInterviewSession.js";
import { useLiveAvatar } from "../../hooks/useLiveAvatar.js";
import { useSpeechSynthesis } from "../../hooks/useSpeechSynthesis.js";
import { Button } from "../ui/Button.jsx";
import { ConfirmDialog } from "../ui/ConfirmDialog.jsx";
import { AnswerDock } from "./AnswerDock.jsx";
import { validateAudioFileClient } from "./AnswerInput.jsx";
import { InterviewCompletionDialog } from "./InterviewCompletionDialog.jsx";
import { InterviewHeader } from "./InterviewHeader.jsx";
import { InterviewStage } from "./InterviewStage.jsx";
import { QuestionDisplay } from "./QuestionDisplay.jsx";

function StudioSkeleton() {
  return (
    <div className="min-h-screen bg-[#F8FAFC]" aria-label="Loading interview workspace">
      <div className="h-14 border-b border-white/10 bg-[#070D19]" />
      <div className="mx-auto max-w-5xl animate-pulse space-y-4 px-4 py-6 sm:px-6">
        <div className="h-80 rounded-2xl bg-[#0B1528]" />
        <div className="h-24 rounded-2xl border border-slate-200 bg-white" />
        <div className="h-48 rounded-2xl border border-slate-200 bg-white" />
      </div>
    </div>
  );
}

export function InterviewStudio({ sessionId }) {
  const {
    session,
    isAdaptive,
    currentQuestion,
    currentQuestionKind,
    currentIndex,
    totalQuestions,
    answeredCount,
    mainQuestionsCount,
    maxMainQuestions,
    isCompleted,
    isLoading,
    loadError,
    answerError,
    setAnswerError,
    uploadProgress,
    lastEvaluation,
    setLastEvaluation,
    isSubmitting,
    isSkipping,
    isEnding,
    endError,
    setEndError,
    loadWorkspace,
    submitCandidateResponse,
    skipCurrentQuestion,
    finishInterview,
  } = useInterviewSession(sessionId);

  const tts = useSpeechSynthesis();
  const recorder = useAudioRecorder();
  const liveAvatar = useLiveAvatar({
    sessionId: session?.id || sessionId,
    isSessionCompleted: isCompleted,
  });

  const [answerMode, setAnswerMode] = useState("text"); // "text" | "voice"
  const [answerText, setAnswerText] = useState("");
  const [audioFile, setAudioFile] = useState(null);
  const [isSkipDialogOpen, setIsSkipDialogOpen] = useState(false);
  const [isEndDialogOpen, setIsEndDialogOpen] = useState(false);

  const stopAllNarration = useCallback(() => {
    tts.stop();
    liveAvatar.interruptAvatar();
  }, [tts.stop, liveAvatar.interruptAvatar]);

  // Mutual exclusion: speak with LiveAvatar when connected, otherwise browser SpeechSynthesis
  const handleSpeakQuestion = useCallback(
    async (text) => {
      const promptText = (text || currentQuestion?.text || "").trim();
      if (!promptText) return;

      if (liveAvatar.isConnected) {
        tts.stop();
        await liveAvatar.speakWithAvatar(promptText);
      } else {
        tts.speak(promptText);
      }
    },
    [currentQuestion?.text, liveAvatar.isConnected, liveAvatar.speakWithAvatar, tts.speak, tts.stop]
  );

  const handleReplayQuestion = useCallback(
    async (text) => {
      const promptText = (text || currentQuestion?.text || "").trim();
      if (!promptText) return;

      if (liveAvatar.isConnected) {
        tts.stop();
        await liveAvatar.interruptAvatar();
        await liveAvatar.speakWithAvatar(promptText);
      } else {
        tts.replay(promptText);
      }
    },
    [
      currentQuestion?.text,
      liveAvatar.interruptAvatar,
      liveAvatar.isConnected,
      liveAvatar.speakWithAvatar,
      tts.replay,
      tts.stop,
    ]
  );

  // Stop any ongoing speech when switching questions or completing session
  useEffect(() => {
    stopAllNarration();
  }, [currentQuestion?.id, isCompleted, stopAllNarration]);

  // Warn before accidental browser tab refresh/close if there is an unsaved draft or recording
  const hasDraftAnswer = Boolean(
    answerText.trim() ||
      audioFile ||
      recorder.audioBlob ||
      recorder.recordingState === "recording" ||
      recorder.recordingState === "paused"
  );

  useEffect(() => {
    if (!hasDraftAnswer || isCompleted) return undefined;
    const handleBeforeUnload = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasDraftAnswer, isCompleted]);

  function handleAudioFileChange(file) {
    setAnswerError("");
    if (!file) {
      setAudioFile(null);
      return;
    }
    const validation = validateAudioFileClient(file);
    if (!validation.valid) {
      setAudioFile(null);
      setAnswerError(validation.error);
      return;
    }
    setAudioFile(file);
  }

  async function handleStartVoiceRecording() {
    setAnswerError("");
    stopAllNarration();
    await recorder.startRecording();
  }

  async function handleAnswerSubmit() {
    if (isSubmitting || isSkipping || isEnding || isCompleted) return;

    if (
      recorder.recordingState === "recording" ||
      recorder.recordingState === "paused"
    ) {
      setAnswerError(
        "Please stop your voice recording before submitting your answer."
      );
      return;
    }

    setAnswerError("");
    const trimmed = answerText.trim();
    const activeAudioBlob = recorder.audioBlob || audioFile;
    const activeAudioName = recorder.audioBlob
      ? recorder.audioFilename
      : audioFile?.name || "";

    if (!trimmed && !activeAudioBlob) {
      setAnswerError(
        answerMode === "voice"
          ? "Please record a voice answer or enter a text answer before submitting."
          : "Please enter your answer before submitting."
      );
      return;
    }

    if (audioFile && !recorder.audioBlob) {
      const audioValidation = validateAudioFileClient(audioFile);
      if (!audioValidation.valid) {
        setAnswerError(audioValidation.error);
        return;
      }
    }

    stopAllNarration();

    const result = await submitCandidateResponse({
      answerText: trimmed,
      audioBlob: activeAudioBlob,
      audioFilename: activeAudioName,
    });

    if (result?.ok) {
      setAnswerText("");
      setAudioFile(null);
      recorder.discardRecording();
    }
  }

  function handleRequestSkip() {
    if (isSubmitting || isSkipping || isEnding || isCompleted) return;
    setIsSkipDialogOpen(true);
  }

  async function handleConfirmSkip() {
    if (isSubmitting || isSkipping || isEnding || isCompleted) return;
    stopAllNarration();

    const result = await skipCurrentQuestion();
    setIsSkipDialogOpen(false);

    if (result?.ok) {
      setAnswerText("");
      setAudioFile(null);
      recorder.discardRecording();
    }
  }

  function handleRequestEndInterview() {
    if (isSubmitting || isSkipping || isEnding) return;
    setEndError("");
    setIsEndDialogOpen(true);
  }

  async function handleConfirmEndInterview() {
    if (isSubmitting || isSkipping || isEnding) return;
    stopAllNarration();
    recorder.discardRecording();
    await liveAvatar.disconnectAvatar();

    const result = await finishInterview();
    if (result?.ok) {
      setIsEndDialogOpen(false);
    }
  }

  if (isLoading) {
    return <StudioSkeleton />;
  }

  if (loadError) {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col justify-center px-4 py-12">
        <div
          role="alert"
          className="space-y-4 rounded-2xl border border-destructive/30 bg-white p-6 shadow-sm sm:p-8"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-6 w-6 shrink-0 text-destructive" aria-hidden="true" />
            <div>
              <h1 className="font-display text-lg font-bold text-slate-900">
                Unable to load interview session
              </h1>
              <p className="mt-1 text-sm text-slate-600">{loadError}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button type="button" variant="primary" size="sm" onClick={loadWorkspace}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              <span>Retry</span>
            </Button>
            <Link to="/dashboard">
              <Button type="button" variant="secondary" size="sm">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                <span>Back to Dashboard</span>
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const isBusy = isSubmitting || isSkipping || isEnding;
  const remainingCount = Math.max(0, totalQuestions - answeredCount);

  const isNarrating = Boolean(
    liveAvatar.isAvatarSpeaking || (tts.isSpeaking && !tts.isPaused)
  );

  const avatarState =
    isSubmitting || isSkipping
      ? "evaluating"
      : isNarrating
      ? "speaking"
      : recorder.recordingState === "recording" ||
        recorder.recordingState === "paused" ||
        answerText.trim().length > 0
      ? "listening"
      : "idle";

  return (
    <div className="flex min-h-screen flex-col bg-[#F1F5F9]">
      {/* 1. Compact Top Navigation */}
      <InterviewHeader
        session={{ ...session, completed: isCompleted }}
        isAdaptive={isAdaptive}
        currentIndex={currentIndex}
        totalQuestions={totalQuestions}
        answeredCount={answeredCount}
        mainQuestionsCount={mainQuestionsCount}
        maxMainQuestions={maxMainQuestions}
        isAvatarConnected={liveAvatar.isConnected}
        isBusy={isBusy}
        onRequestEndInterview={handleRequestEndInterview}
      />

      {/* 2–4. Single Focal-Point Stage + Question Strip + Unified Bottom Control Dock */}
      <main
        id="interview-main-stage"
        className="mx-auto flex w-full max-w-7xl flex-1 flex-col justify-between gap-4 px-4 py-4 sm:px-6 sm:py-5"
      >
        {isCompleted || !currentQuestion ? (
          <section
            aria-label="Interview completed"
            className="mx-auto my-auto max-w-xl rounded-2xl border border-slate-200/90 bg-white p-6 text-center shadow-sm sm:p-8"
          >
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-success-bg text-success">
              <CheckCircle2 className="h-6 w-6" aria-hidden="true" />
            </div>
            <h1 className="mt-4 font-display text-xl font-bold text-slate-900">
              Interview Session Completed
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              All questions for this session have been completed. You can now review your performance summary.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <Link to={`/sessions/${session?.id || sessionId}/summary`}>
                <Button variant="primary" size="md">
                  <FileBarChart className="h-4 w-4" aria-hidden="true" />
                  <span>View Session Summary</span>
                </Button>
              </Link>
              <Link to="/dashboard">
                <Button variant="secondary" size="md">
                  Back to Dashboard
                </Button>
              </Link>
            </div>
          </section>
        ) : (
          <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-12">
            {/* Left / Dominant Focal Point (7 cols): Full Uncropped 16:9 AI Interviewer Video Stage */}
            <div className="lg:col-span-7">
              <InterviewStage
                session={session}
                question={currentQuestion}
                avatarState={avatarState}
                liveAvatar={liveAvatar}
                tts={tts}
                recordingState={recorder.recordingState}
                recordingDuration={recorder.durationSeconds}
                isCompleted={isCompleted}
                isBusy={isBusy}
                onSpeakQuestion={handleSpeakQuestion}
                onReplayQuestion={handleReplayQuestion}
              />
            </div>

            {/* Right Column (5 cols): Current Question + Unified Answer Dock at eye-level */}
            <div className="space-y-4 lg:col-span-5">
              <QuestionDisplay
                question={currentQuestion}
                isAdaptive={isAdaptive}
                questionKind={currentQuestionKind}
                currentIndex={currentIndex}
                totalQuestions={totalQuestions}
                lastEvaluation={isAdaptive ? null : lastEvaluation}
                onDismissEvaluation={() => setLastEvaluation(null)}
              />

              <AnswerDock
                answerMode={answerMode}
                onAnswerModeChange={setAnswerMode}
                answerText={answerText}
                onAnswerTextChange={setAnswerText}
                audioFile={audioFile}
                onAudioFileChange={handleAudioFileChange}
                recorder={{
                  ...recorder,
                  onStartRecording: handleStartVoiceRecording,
                }}
                error={answerError}
                onClearError={() => setAnswerError("")}
                uploadProgress={uploadProgress}
                isSubmitting={isSubmitting}
                isSkipping={isSkipping}
                isEnding={isEnding}
                onSubmit={handleAnswerSubmit}
                onSkip={handleRequestSkip}
              />
            </div>
          </div>
        )}
      </main>

      {/* Skip Question Confirmation Dialog */}
      <ConfirmDialog
        isOpen={isSkipDialogOpen}
        title="Skip this question?"
        description={
          hasDraftAnswer
            ? "You have an unsaved response or recording. Skipping this question will discard your draft and record a score of 0 for this prompt."
            : "Skipping this question will record a score of 0 and move to the next question."
        }
        confirmLabel="Skip Question"
        cancelLabel="Keep Answering"
        variant="destructive"
        isLoading={isSkipping}
        loadingLabel="Skipping..."
        onConfirm={handleConfirmSkip}
        onCancel={() => {
          if (!isSkipping) setIsSkipDialogOpen(false);
        }}
      />

      {/* End Interview Confirmation Dialog */}
      <InterviewCompletionDialog
        isOpen={isEndDialogOpen}
        remainingCount={remainingCount}
        hasUnsavedDraft={hasDraftAnswer}
        isEnding={isEnding}
        error={endError}
        onConfirm={handleConfirmEndInterview}
        onCancel={() => {
          if (!isEnding) {
            setIsEndDialogOpen(false);
            setEndError("");
          }
        }}
      />
    </div>
  );
}
