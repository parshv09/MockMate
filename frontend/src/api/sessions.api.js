import { apiClient } from "./client.js";

/**
 * Interview Sessions API service module (/api/v1/sessions/*)
 */
export const SESSION_ENDPOINTS = {
  listCreate: "/sessions/",
  createResumeJd: "/sessions/resume-jd/",
  detail: (id) => `/sessions/${id}/`,
  nextQuestion: (id) => `/sessions/${id}/next-question/`,
  submitAnswer: (id) => `/sessions/${id}/answers/`,
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
