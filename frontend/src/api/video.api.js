import { apiClient } from "./client.js";

/**
 * Video behavior analysis API module (/api/v1/sessions/:id/video/*)
 *
 * Frame contract (VideoFrameUploadSerializer):
 * - multipart field `frame`: JPEG, PNG or WEBP image, max 5 MB
 * - optional `frame_id` (max 128 chars) used by the server to de-duplicate retries
 */
export const VIDEO_ENDPOINTS = {
  frame: (sessionId) => `/sessions/${sessionId}/video/frame/`,
  metrics: (sessionId) => `/sessions/${sessionId}/video/metrics/`,
  finalize: (sessionId) => `/sessions/${sessionId}/video/finalize/`,
};

export const MAX_VIDEO_FRAME_BYTES = 5 * 1024 * 1024;

/** → { status: "ok", session_id, faces, eye_contact, head_movement } */
export async function uploadVideoFrame(sessionId, frameBlob, frameId = "") {
  const formData = new FormData();
  formData.append("frame", frameBlob, "frame.jpg");
  if (frameId) {
    formData.append("frame_id", String(frameId).slice(0, 128));
  }
  const response = await apiClient.post(VIDEO_ENDPOINTS.frame(sessionId), formData);
  return response.data;
}
