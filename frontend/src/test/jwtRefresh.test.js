import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient, setAuthFailureHandler } from "../api/client.js";
import { tokenStorage } from "../utils/tokenStorage.js";

describe("JWT Axios Interceptor Lifecycle", () => {
  beforeEach(() => {
    tokenStorage.clearTokens();
    setAuthFailureHandler(null);
    vi.restoreAllMocks();
  });

  it("attaches Bearer access token to protected requests", async () => {
    tokenStorage.setTokens({ access: "access-123", refresh: "refresh-123" });

    let capturedAuthHeader = null;
    const response = await apiClient.get("/sessions/", {
      adapter: async (config) => {
        capturedAuthHeader = config.headers.Authorization;
        return { data: [], status: 200, statusText: "OK", headers: {}, config };
      },
    });

    expect(response.status).toBe(200);
    expect(capturedAuthHeader).toBe("Bearer access-123");
  });

  it("refreshes expired access token once for concurrent 401 requests and retries both", async () => {
    tokenStorage.setTokens({ access: "expired-access", refresh: "valid-refresh" });

    const refreshSpy = vi.spyOn(axios, "post").mockResolvedValueOnce({
      data: { access: "fresh-access" },
      status: 200,
    });

    let callCount = 0;
    const adapter = vi.fn(async (config) => {
      callCount += 1;
      if (config.headers.Authorization === "Bearer expired-access") {
        const error = new Error("Unauthorized");
        error.config = config;
        error.response = { status: 401, data: { detail: "Token expired" } };
        throw error;
      }
      return {
        data: { ok: true, call: callCount },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    });

    const [res1, res2] = await Promise.all([
      apiClient.get("/sessions/", { adapter }),
      apiClient.get("/resumes/", { adapter }),
    ]);

    expect(refreshSpy).toHaveBeenCalledTimes(1);
    expect(refreshSpy).toHaveBeenCalledWith(
      expect.stringContaining("/auth/refresh/"),
      { refresh: "valid-refresh" },
      expect.any(Object)
    );
    expect(tokenStorage.getAccessToken()).toBe("fresh-access");
    expect(res1.status).toBe(200);
    expect(res2.status).toBe(200);
  });

  it("clears tokens and triggers auth failure handler when refresh fails", async () => {
    tokenStorage.setTokens({ access: "expired-access", refresh: "invalid-refresh" });
    const onAuthFailure = vi.fn();
    setAuthFailureHandler(onAuthFailure);

    vi.spyOn(axios, "post").mockRejectedValueOnce({
      response: { status: 401, data: { detail: "Token is invalid or expired" } },
    });

    const adapter = vi.fn(async (config) => {
      const error = new Error("Unauthorized");
      error.config = config;
      error.response = { status: 401, data: { detail: "Token expired" } };
      throw error;
    });

    await expect(apiClient.get("/sessions/", { adapter })).rejects.toBeDefined();

    expect(tokenStorage.getAccessToken()).toBeNull();
    expect(tokenStorage.getRefreshToken()).toBeNull();
    expect(onAuthFailure).toHaveBeenCalledTimes(1);
  });

  it("does not loop infinitely if retried request also returns 401", async () => {
    tokenStorage.setTokens({ access: "expired-access", refresh: "valid-refresh" });
    const refreshSpy = vi.spyOn(axios, "post").mockResolvedValueOnce({
      data: { access: "still-rejected-access" },
      status: 200,
    });

    const adapter = vi.fn(async (config) => {
      const error = new Error("Unauthorized");
      error.config = config;
      error.response = { status: 401, data: { detail: "Unauthorized" } };
      throw error;
    });

    await expect(apiClient.get("/sessions/", { adapter })).rejects.toBeDefined();
    expect(refreshSpy).toHaveBeenCalledTimes(1);
    expect(adapter).toHaveBeenCalledTimes(2);
  });
});

