import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import * as authApi from "../api/auth.api.js";
import * as resumesApi from "../api/resumes.api.js";
import * as sessionsApi from "../api/sessions.api.js";
import { tokenStorage } from "../utils/tokenStorage.js";

function renderSessionSetup() {
  tokenStorage.setTokens({ access: "valid-access", refresh: "valid-refresh" });
  vi.spyOn(authApi, "fetchCurrentUser").mockResolvedValue({
    id: 1,
    username: "alexchen",
    email: "alex@example.com",
    first_name: "Alex",
    last_name: "Chen",
    user_type: "job_seeker",
    target_role: "Backend Engineer",
  });

  return render(
    <AuthProvider>
      <ToastProvider>
        <MemoryRouter initialEntries={["/sessions/new"]}>
          <AppRoutes />
        </MemoryRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

const SAMPLE_RESUMES = [
  {
    id: 15,
    title: "Backend Python CV",
    file_name: "alex_backend.pdf",
    has_file: true,
    created_at: "2026-11-10T10:00:00Z",
    updated_at: "2026-11-12T10:00:00Z",
  },
  {
    id: 16,
    title: "Full Stack CV",
    file_name: "alex_fullstack.md",
    has_file: true,
    created_at: "2026-11-08T10:00:00Z",
    updated_at: "2026-11-08T10:00:00Z",
  },
];

describe("Interview Setup (/sessions/new)", () => {
  beforeEach(() => {
    tokenStorage.clearTokens();
    vi.restoreAllMocks();
  });

  it("loads standard interview setup with user's target role", async () => {
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue(SAMPLE_RESUMES);

    renderSessionSetup();

    expect(
      await screen.findByRole("heading", { name: /start a new interview/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /quick start/i })
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText(/target job role/i)).toHaveValue("Backend Engineer");
  });

  it("creates a standard interview with exact expected payload and navigates to session route", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue([]);
    const createSpy = vi
      .spyOn(sessionsApi, "createStandardSession")
      .mockResolvedValueOnce({
        message: "Standard interview session created successfully.",
        created_questions: 4,
        session: { id: 88, role: "beh", job_role: "Tech Lead", difficulty: 4, total_questions: 4 },
      });

    renderSessionSetup();
    await screen.findByRole("heading", { name: /start a new interview/i });

    await user.selectOptions(screen.getByLabelText(/interview focus/i), "beh");
    const jobRoleInput = screen.getByLabelText(/target job role/i);
    await user.clear(jobRoleInput);
    await user.type(jobRoleInput, "Tech Lead");
    await user.selectOptions(screen.getByLabelText(/difficulty level/i), "4");
    const countInput = screen.getByLabelText(/number of questions/i);
    await user.clear(countInput);
    await user.type(countInput, "4");

    await user.click(screen.getByRole("button", { name: /^start standard interview$/i }));

    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1));
    expect(createSpy).toHaveBeenCalledWith({
      role: "beh",
      job_role: "Tech Lead",
      difficulty: 4,
      n_questions: 4,
    });

    // Navigates to /sessions/88/interview (placeholder InterviewWorkspacePage)
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: /start a new interview/i })).not.toBeInTheDocument();
    });
  });

  it("loads resumes, validates Resume + JD, sends exact payload, and navigates", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue(SAMPLE_RESUMES);
    const createSpy = vi
      .spyOn(sessionsApi, "createResumeJdSession")
      .mockResolvedValueOnce({
        message: "Resume & JD tailored interview session created successfully.",
        created_questions: 6,
        session: { id: 95, has_resume: true, resume_id: 15, difficulty: 5, total_questions: 6 },
      });

    renderSessionSetup();
    await screen.findByRole("heading", { name: /start a new interview/i });

    await user.click(screen.getByRole("button", { name: /resume \+ job description/i }));

    // Resumes listed with file name
    expect(screen.getByText("Backend Python CV")).toBeInTheDocument();
    expect(screen.getByText("alex_backend.pdf")).toBeInTheDocument();

    // Validation when neither resume nor JD is provided
    await user.click(screen.getByRole("button", { name: /start tailored interview/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /please select a saved resume or paste a job description/i
    );
    expect(createSpy).not.toHaveBeenCalled();

    // Select resume 15 and enter JD
    await user.click(screen.getByRole("button", { name: /backend python cv/i }));
    await user.type(
      screen.getByLabelText(/job description/i, { selector: "textarea" }),
      "Senior Django & PostgreSQL Engineer"
    );
    await user.selectOptions(screen.getByLabelText(/difficulty level/i), "5");
    const countInput = screen.getByLabelText(/number of questions/i);
    await user.clear(countInput);
    await user.type(countInput, "6");

    await user.click(screen.getByRole("button", { name: /start tailored interview/i }));

    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1));
    expect(createSpy).toHaveBeenCalledWith({
      resume_id: 15,
      job_description: "Senior Django & PostgreSQL Engineer",
      difficulty: 5,
      n_questions: 6,
    });

    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: /start a new interview/i })).not.toBeInTheDocument();
    });
  });

  it("displays DRF validation errors and prevents duplicate submissions", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue([]);

    let rejectRequest;
    const createSpy = vi
      .spyOn(sessionsApi, "createStandardSession")
      .mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            rejectRequest = reject;
          })
      );

    renderSessionSetup();
    await screen.findByRole("heading", { name: /start a new interview/i });

    const submitBtn = screen.getByRole("button", { name: /^start standard interview$/i });
    await user.click(submitBtn);
    await user.click(submitBtn); // Second click while in flight must be ignored

    expect(createSpy).toHaveBeenCalledTimes(1);
    expect(submitBtn).toBeDisabled();

    rejectRequest({
      response: {
        status: 400,
        data: { n_questions: ["Ensure this value is less than or equal to 30."] },
      },
    });

    expect(
      await screen.findAllByText(/ensure this value is less than or equal to 30/i)
    ).not.toHaveLength(0);
  });

  it("handles empty resume list and API failure with Retry", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes")
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce([]);

    renderSessionSetup();
    await screen.findByRole("heading", { name: /start a new interview/i });

    await user.click(screen.getByRole("button", { name: /resume \+ job description/i }));

    expect(
      await screen.findByText(/unable to reach the mockmate server/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /retry/i }));

    expect(
      await screen.findByText(/no saved resumes available/i)
    ).toBeInTheDocument();
  });

  it("redirects unauthenticated users to /login", async () => {
    tokenStorage.clearTokens();
    render(
      <AuthProvider>
        <ToastProvider>
          <MemoryRouter initialEntries={["/sessions/new"]}>
            <AppRoutes />
          </MemoryRouter>
        </ToastProvider>
      </AuthProvider>
    );

    expect(
      await screen.findByRole("heading", { name: /sign in to mockmate/i })
    ).toBeInTheDocument();
  });
});

