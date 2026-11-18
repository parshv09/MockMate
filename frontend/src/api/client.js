import axios from "axios";
import { tokenStorage } from "../utils/tokenStorage.js";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Accept: "application/json",
  },
});

const AUTH_BYPASS_PATHS = ["/auth/login/", "/auth/register/", "/auth/refresh/"];

let refreshPromise = null;
let authFailureHandler = null;

/**
 * Registers a callback invoked whenever token refresh fails or tokens are
 * rejected unrecoverably, allowing AuthContext to clear React user state.
 */
export function setAuthFailureHandler(handler) {
  authFailureHandler = typeof handler === "function" ? handler : null;
}

function isAuthBypassRequest(url = "") {
  return AUTH_BYPASS_PATHS.some((path) => url.includes(path));
}

function notifyAuthFailure() {
  tokenStorage.clearTokens();
  if (authFailureHandler) {
    authFailureHandler();
  }
}

async function performSingleFlightRefresh() {
  if (refreshPromise) {
    return refreshPromise;
  }

  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) {
    return Promise.reject(new Error("No refresh token available."));
  }

  refreshPromise = axios
    .post(
      `${API_BASE_URL}/auth/refresh/`,
      { refresh: refreshToken },
      {
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
      }
    )
    .then((response) => {
      const { access, refresh } = response.data || {};
      if (!access) {
        throw new Error("Refresh response did not include an access token.");
      }
      tokenStorage.setTokens({
        access,
        refresh: refresh || refreshToken,
      });
      return access;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

apiClient.interceptors.request.use(
  (config) => {
    const accessToken = tokenStorage.getAccessToken();
    if (accessToken && !isAuthBypassRequest(config.url)) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config;
    const status = error?.response?.status;

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      isAuthBypassRequest(originalRequest.url)
    ) {
      return Promise.reject(error);
    }

    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) {
      notifyAuthFailure();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      const newAccessToken = await performSingleFlightRefresh();
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      notifyAuthFailure();
      return Promise.reject(refreshError);
    }
  }
);
