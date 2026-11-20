import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  endSession,
  fetchNextQuestion,
  fetchSessionDetail,
  skipQuestion,
  submitAnswer,
} from "../api/sessions.api.js";
import { useToast } from "../context/ToastContext.jsx";
import { extractApiError } from "../utils/apiErrors.js";

/**
 * Manages the active interview session lifecycle:
 * - Loading session metadata & current unprocessed question
 * - Submitting voice (recorded Blob or uploaded file) and text answers
 * - Tracking upload progress and preserving drafts on failure
 * - Skipping questions with confirmation
 * - Ending the session with confirmation and navigating to the summary page
 */
export function useInterviewSession(sessionId) {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [session, setSession] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [currentAnswerId, setCurrentAnswerId] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [answerError, setAnswerError] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [lastEvaluation, setLastEvaluation] = useState(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSkipping, setIsSkipping] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [endError, setEndError] = useState("");

  const loadWorkspace = useCallback(async () => {
    setIsLoading(true);
    setLoadError("");

    try {
      const [sessionData, nextData] = await Promise.all([
        fetchSessionDetail(sessionId),
        fetchNextQuestion(sessionId),
      ]);

      setSession(sessionData);
      const total =
        nextData?.total_questions ?? sessionData?.total_questions ?? 0;
      const answered = sessionData?.answered_count ?? 0;
      const completed = Boolean(
        sessionData?.completed ||
          sessionData?.is_completed ||
          nextData?.is_completed ||
          !nextData?.has_next_question
      );

      setTotalQuestions(total);
      setAnsweredCount(answered);
      setIsCompleted(completed);

      if (nextData?.has_next_question && nextData?.question) {
        setCurrentQuestion(nextData.question);
        setCurrentAnswerId(nextData.answer_id ?? null);
        setCurrentIndex(nextData.current_index ?? answered + 1);
      } else {
        setCurrentQuestion(null);
        setCurrentAnswerId(null);
        setCurrentIndex(total || 1);
      }
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Unable to load this interview session. It may not exist or you may not have access."
      );
      setLoadError(parsed.message);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  const submitCandidateResponse = useCallback(
    async ({ answerText = "", audioBlob = null, audioFilename = "" } = {}) => {
      if (isSubmitting || isSkipping || isEnding || isCompleted) {
        return { ok: false };
      }

      setAnswerError("");
      setUploadProgress(0);
      setIsSubmitting(true);

      try {
        const data = await submitAnswer(sessionId, {
          answerId: currentAnswerId,
          answerText,
          audioBlob,
          audioFilename,
          onUploadProgress: (evt) => {
            if (evt?.total) {
              setUploadProgress(
                Math.min(100, Math.round((evt.loaded * 100) / evt.total))
              );
            }
          },
        });

        const evaluatedAnswer = data?.answer || null;
        const sessionDone = Boolean(
          data?.is_session_completed || !data?.next_question
        );

        setLastEvaluation(evaluatedAnswer);
        setAnsweredCount((prev) => prev + 1);

        if (sessionDone) {
          setIsCompleted(true);
          setCurrentQuestion(null);
          setCurrentAnswerId(null);
          showToast({
            title: "Interview completed",
            description: "All questions have been answered. Loading your summary...",
            tone: "success",
          });
          navigate(`/sessions/${session?.id || sessionId}/summary`);
        } else {
          setCurrentQuestion(data.next_question);
          setCurrentAnswerId(null);
          setCurrentIndex((prev) =>
            typeof evaluatedAnswer?.index === "number"
              ? evaluatedAnswer.index + 1
              : prev + 1
          );
        }

        return { ok: true, answer: evaluatedAnswer, isCompleted: sessionDone };
      } catch (error) {
        const parsed = extractApiError(
          error,
          "Failed to submit your answer. Your response has been preserved — please try again."
        );
        const fieldMsg =
          parsed.fieldErrors.answer_text ||
          parsed.fieldErrors.audio_file ||
          parsed.message;
        setAnswerError(fieldMsg);
        return { ok: false, error: fieldMsg };
      } finally {
        setIsSubmitting(false);
        setUploadProgress(0);
      }
    },
    [
      currentAnswerId,
      isCompleted,
      isEnding,
      isSkipping,
      isSubmitting,
      navigate,
      session?.id,
      sessionId,
      showToast,
    ]
  );

  const skipCurrentQuestion = useCallback(async () => {
    if (isSubmitting || isSkipping || isEnding || isCompleted) {
      return { ok: false };
    }

    setIsSkipping(true);
    setAnswerError("");

    try {
      const data = await skipQuestion(sessionId, {
        answerId: currentAnswerId,
      });

      const skippedAnswer = data?.answer || null;
      const sessionDone = Boolean(
        data?.is_session_completed || !data?.next_question
      );

      setLastEvaluation(skippedAnswer);
      setAnsweredCount((prev) => prev + 1);

      if (sessionDone) {
        setIsCompleted(true);
        setCurrentQuestion(null);
        setCurrentAnswerId(null);
        showToast({
          title: "Interview completed",
          description: "Moving to your session summary.",
          tone: "info",
        });
        navigate(`/sessions/${session?.id || sessionId}/summary`);
      } else {
        setCurrentQuestion(data.next_question);
        setCurrentAnswerId(null);
        setCurrentIndex((prev) =>
          typeof skippedAnswer?.index === "number"
            ? skippedAnswer.index + 1
            : prev + 1
        );
        showToast({
          title: "Question skipped",
          description: "Moved to the next question.",
          tone: "info",
        });
      }

      return { ok: true, isCompleted: sessionDone };
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Unable to skip this question right now. Please try again."
      );
      setAnswerError(parsed.message);
      return { ok: false, error: parsed.message };
    } finally {
      setIsSkipping(false);
    }
  }, [
    currentAnswerId,
    isCompleted,
    isEnding,
    isSkipping,
    isSubmitting,
    navigate,
    session?.id,
    sessionId,
    showToast,
  ]);

  const finishInterview = useCallback(async () => {
    if (isSubmitting || isSkipping || isEnding) {
      return { ok: false };
    }

    setIsEnding(true);
    setEndError("");

    try {
      const data = await endSession(sessionId);
      const resolvedId = data?.session?.id || session?.id || sessionId;
      setIsCompleted(true);
      showToast({
        title: "Interview ended",
        description: "Your interview session has been finalized.",
        tone: "info",
      });
      navigate(`/sessions/${resolvedId}/summary`);
      return { ok: true };
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Could not end the interview session. Please try again."
      );
      setEndError(parsed.message);
      return { ok: false, error: parsed.message };
    } finally {
      setIsEnding(false);
    }
  }, [
    isEnding,
    isSkipping,
    isSubmitting,
    navigate,
    session?.id,
    sessionId,
    showToast,
  ]);

  return {
    session,
    currentQuestion,
    currentAnswerId,
    currentIndex,
    totalQuestions,
    answeredCount,
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
  };
}

