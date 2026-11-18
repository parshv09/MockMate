/**
 * Token storage utility for MockMate JWT authentication.
 *
 * Security approach:
 * - The Django backend uses SimpleJWT with Bearer Authorization headers and
 *   does not issue HttpOnly auth cookies.
 * - Storing both access and refresh tokens in localStorage under namespaced
 *   keys enables seamless session restoration across full page reloads while
 *   keeping token access isolated behind this single module.
 * - Tokens are cleared immediately on logout or unrecoverable refresh failure.
 * - Never store raw passwords or sensitive PII in token storage.
 */

const ACCESS_TOKEN_KEY = "mockmate_access_token";
const REFRESH_TOKEN_KEY = "mockmate_refresh_token";

export const tokenStorage = {
  getAccessToken() {
    try {
      return window.localStorage.getItem(ACCESS_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  getRefreshToken() {
    try {
      return window.localStorage.getItem(REFRESH_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  setTokens({ access, refresh }) {
    try {
      if (access) {
        window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
      }
      if (refresh) {
        window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
      }
    } catch {
      // Ignore storage quota / privacy mode errors cleanly
    }
  },

  clearTokens() {
    try {
      window.localStorage.removeItem(ACCESS_TOKEN_KEY);
      window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    } catch {
      // Ignore storage errors cleanly
    }
  },

  hasTokens() {
    return Boolean(this.getAccessToken() || this.getRefreshToken());
  },
};

