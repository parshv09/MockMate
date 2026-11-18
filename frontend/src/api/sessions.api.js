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
