import { apiClient } from "./client.js";

/**
 * Resume Vault API service module (/api/v1/resumes/*)
 */
export const RESUME_ENDPOINTS = {
  listCreate: "/resumes/",
  detail: (id) => `/resumes/${id}/`,
};

export async function fetchResumes() {
  const response = await apiClient.get(RESUME_ENDPOINTS.listCreate);
  return Array.isArray(response.data) ? response.data : [];
}
