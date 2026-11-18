import { apiClient } from "./client.js";

/**
 * Authentication API service module (/api/v1/auth/*)
 * Matches Django SimpleJWT + custom RegisterAPIView/LoginAPIView/MeAPIView contracts.
 * Note: Backend is stateless JWT and does not expose a logout endpoint.
 */
export const AUTH_ENDPOINTS = {
  register: "/auth/register/",
  login: "/auth/login/",
  refresh: "/auth/refresh/",
  me: "/auth/me/",
};

export async function registerUser(payload) {
  const response = await apiClient.post(AUTH_ENDPOINTS.register, payload);
  return response.data;
}

export async function loginUser(payload) {
  const response = await apiClient.post(AUTH_ENDPOINTS.login, payload);
  return response.data;
}

export async function fetchCurrentUser() {
  const response = await apiClient.get(AUTH_ENDPOINTS.me);
  return response.data;
}
