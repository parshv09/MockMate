import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import * as authApi from "../api/auth.api.js";
import * as sessionsApi from "../api/sessions.api.js";
import * as resumesApi from "../api/resumes.api.js";
import { tokenStorage } from "../utils/tokenStorage.js";

function renderAuthenticatedDashboard() {
  tokenStorage.setTokens({ access: "valid-access", refresh: "valid-refresh" });
  vi.spyOn(authApi, "fetchCurrentUser").mockResolvedValue({
    id: 1,
    username: "alexchen",
    email: "alex@example.com",
    first_name: "Alex",
    last_name: "Chen",
    user_type: "job_seeker",
    target_role: "Software Engineer",
  });

  return render(
    <AuthProvider>
      <ToastProvider>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <AppRoutes />
        </MemoryRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

describe("Authenticated Dashboard & Navigation", () => {
  beforeEach(() => {
    tokenStorage.clearTokens();
    vi.restoreAllMocks();
  });

  it("renders derived statistics, recent sessions, and saved resumes from real APIs", async () => {
    vi.spyOn(sessionsApi, "fetchSessions").mockResolvedValueOnce([
      {
        id: 12,
        role: "tech",
        job_role: "Backend Engineer",
        difficulty: 3,
        total_questions: 5,
        answered_count: 5,
        completed: true,
        total_score: 84,
        duration: 420,
        started_at: "2026-11-10T10:00:00Z",
        has_resume: true,
        has_job_description: true,
      },
      {
        id: 11,
        role: "beh",
        job_role: "Product Engineer",
        difficulty: 2,
        total_questions: 4,
        answered_count: 4,
        completed: true,
        total_score: 76,
        duration: 300,
        started_at: "2026-11-08T10:00:00Z",
        has_resume: false,
        has_job_description: false,
      },
    ]);
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValueOnce([
      {
        id: 5,
        title: "Alex Backend CV",
        file_name: "alex_cv.pdf",
        has_file: true,
        created_at: "2026-11-01T10:00:00Z",
        updated_at: "2026-11-01T10:00:00Z",
      },
    ]);

    renderAuthenticatedDashboard();

    expect(
      await screen.findByRole("heading", { name: /welcome back, alex/i })
    ).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
    expect(screen.getAllByText("Backend Engineer").length).toBeGreaterThan(0);
    expect(screen.getByText("Alex Backend CV")).toBeInTheDocument();
  });

  it("renders clean empty states when user has no sessions or resumes", async () => {
    vi.spyOn(sessionsApi, "fetchSessions").mockResolvedValueOnce([]);
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValueOnce([]);

    renderAuthenticatedDashboard();

    expect(
      await screen.findByText(/no interview sessions yet/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/no resumes uploaded/i)).toBeInTheDocument();
  });

  it("renders backend unavailable error state and recovers on Retry", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessions")
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce([]);
    vi.spyOn(resumesApi, "fetchResumes")
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce([]);

    renderAuthenticatedDashboard();

    expect(
      await screen.findByText(/could not load studio data/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /retry/i }));

    expect(
      await screen.findByText(/no interview sessions yet/i)
    ).toBeInTheDocument();
  });

  it("toggles mobile navigation drawer cleanly", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessions").mockResolvedValueOnce([]);
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValueOnce([]);

    renderAuthenticatedDashboard();

    await screen.findByRole("heading", { name: /welcome back, alex/i });

    const menuButton = screen.getByRole("button", {
      name: /open navigation menu/i,
    });
    expect(menuButton).toHaveAttribute("aria-expanded", "false");

    await user.click(menuButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByRole("navigation", { name: /mobile studio navigation/i })
    ).toBeInTheDocument();
  });
});

