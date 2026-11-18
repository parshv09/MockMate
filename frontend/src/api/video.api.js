/**
 * Video Telemetry API service module (/api/v1/sessions/:id/video/*)
 * Endpoints will be wired in the Interview Workspace implementation step.
 */
export const VIDEO_ENDPOINTS = {
  frame: (sessionId) => `/sessions/${sessionId}/video/frame/`,
  metrics: (sessionId) => `/sessions/${sessionId}/video/metrics/`,
  finalize: (sessionId) => `/sessions/${sessionId}/video/finalize/`,
};

