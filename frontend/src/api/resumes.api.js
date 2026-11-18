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

export async function uploadResume({ title = "", file = null, rawText = "", onUploadProgress } = {}) {
  const trimmedTitle = title.trim();

  if (file) {
    const formData = new FormData();
    if (trimmedTitle) {
      formData.append("title", trimmedTitle);
    }
    formData.append("file", file);

    const response = await apiClient.post(RESUME_ENDPOINTS.listCreate, formData, {
      onUploadProgress,
    });
    return response.data;
  }

  const response = await apiClient.post(
    RESUME_ENDPOINTS.listCreate,
    {
      title: trimmedTitle,
      raw_text: rawText.trim(),
    },
    {
      onUploadProgress,
    }
  );
  return response.data;
}

export async function deleteResume(id) {
  await apiClient.delete(RESUME_ENDPOINTS.detail(id));
}
