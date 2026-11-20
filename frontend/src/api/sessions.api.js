import { apiClient } from "./client.js";

/**
 * Interview Sessions API service module (/api/v1/sessions/*)
 */
export const SESSION_ENDPOINTS = {
  listCreate: "/sessions/",
  createResumeJd: "/sessions/resume-jd/",
  detail: (id) => `/sessions/${id}/`,
  nextQuestion: (id) => `/sessions/${id}/next-question/`,
  answers: (id) => `/sessions/${id}/answers/`,
  skipQuestion: (id) => `/sessions/${id}/skip/`,
  endSession: (id) => `/sessions/${id}/end/`,
  summary: (id) => `/sessions/${id}/summary/`,
  reportDownload: (id) => `/sessions/${id}/report/`,
};

export async function fetchSessions() {
  const response = await apiClient.get(SESSION_ENDPOINTS.listCreate);
  return Array.isArray(response.data) ? response.data : [];
}

export async function createStandardSession({
  role = "tech",
  job_role = "Software Engineer",
  difficulty = 3,
  n_questions = 5,
}) {
  const response = await apiClient.post(SESSION_ENDPOINTS.listCreate, {
    role,
    job_role,
    difficulty: Number(difficulty),
    n_questions: Number(n_questions),
  });
  return response.data;
}

export async function createResumeJdSession({
  resume_id = null,
  job_description = "",
  difficulty = 3,
  n_questions = 5,
}) {
  const response = await apiClient.post(SESSION_ENDPOINTS.createResumeJd, {
    resume_id: resume_id ?? null,
    job_description: job_description.trim(),
    difficulty: Number(difficulty),
    n_questions: Number(n_questions),
  });
  return response.data;
}

/** GET /sessions/<id>/ → SessionDetailSerializer */
export async function fetchSessionDetail(sessionId) {
  const response = await apiClient.get(SESSION_ENDPOINTS.detail(sessionId));
  return response.data;
}

/**
 * GET /sessions/<id>/next-question/
 * → { has_next_question: true, session_id, current_index, total_questions, answer_id, question: { id, text, role, difficulty } }
 * → { has_next_question: false, session_id, current_index, total_questions, is_completed, message }
 */
export async function fetchNextQuestion(sessionId) {
  const response = await apiClient.get(SESSION_ENDPOINTS.nextQuestion(sessionId));
  return response.data;
}

/**
 * POST /sessions/<id>/answers/
 * Text answers are sent as JSON. Voice answers are sent as multipart with `audio_file`.
 * → { message, is_session_completed, answer, next_question }
 */
export async function submitAnswer(
  sessionId,
  {
    answerId = null,
    answerText = "",
    audioBlob = null,
    audioFilename = "",
    onUploadProgress,
  } = {}
) {
  if (audioBlob) {
    const formData = new FormData();
    if (answerId !== null && answerId !== undefined) {
      formData.append("answer_id", String(answerId));
    }
    if (answerText.trim()) {
      formData.append("answer_text", answerText.trim());
    }
    formData.append("audio_file", audioBlob, audioFilename || "answer.webm");
    const response = await apiClient.post(
      SESSION_ENDPOINTS.answers(sessionId),
      formData,
      onUploadProgress ? { onUploadProgress } : undefined
    );
    return response.data;
  }

  const response = await apiClient.post(
    SESSION_ENDPOINTS.answers(sessionId),
    {
      answer_id: answerId ?? null,
      answer_text: answerText.trim(),
    },
    onUploadProgress ? { onUploadProgress } : undefined
  );
  return response.data;
}

/** GET /sessions/<id>/answers/ → AnswerEvaluatedSerializer[] */
export async function fetchSessionAnswers(sessionId) {
  const response = await apiClient.get(SESSION_ENDPOINTS.answers(sessionId));
  return Array.isArray(response.data) ? response.data : [];
}

/** POST /sessions/<id>/skip/ → { message, is_session_completed, answer, next_question } */
export async function skipQuestion(sessionId, { answerId = null } = {}) {
  const response = await apiClient.post(SESSION_ENDPOINTS.skipQuestion(sessionId), {
    answer_id: answerId ?? null,
  });
  return response.data;
}

/** POST /sessions/<id>/end/ → { message, session } */
export async function endSession(sessionId) {
  const response = await apiClient.post(SESSION_ENDPOINTS.endSession(sessionId), {});
  return response.data;
}

/** GET /sessions/<id>/summary/ → SessionSummarySerializer (only after completion) */
export async function fetchSessionSummary(sessionId) {
  const response = await apiClient.get(SESSION_ENDPOINTS.summary(sessionId));
  return response.data;
}

/** GET /sessions/<id>/report/ → PDF blob */
export async function downloadSessionReport(sessionId) {
  const response = await apiClient.get(SESSION_ENDPOINTS.reportDownload(sessionId), {
    responseType: "blob",
  });
  return response.data;
}

/** Helper to trigger browser download of the session PDF report */
export async function triggerReportDownload(sessionId, defaultFilename = null) {
  const blob = await downloadSessionReport(sessionId);
  const blobUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = defaultFilename || `AI_Interview_Report_${sessionId}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.URL.revokeObjectURL(blobUrl);
}

