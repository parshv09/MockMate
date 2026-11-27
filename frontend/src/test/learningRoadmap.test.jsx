import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import * as authApi from "../api/auth.api.js";
import * as sessionsApi from "../api/sessions.api.js";
import { tokenStorage } from "../utils/tokenStorage.js";

function renderRoute(initialEntry) {
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
        <MemoryRouter initialEntries={[initialEntry]}>
          <AppRoutes />
        </MemoryRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

const SAMPLE_SUMMARY = {
  session: {
    id: 42,
    role: "tech",
    job_role: "Backend Engineer",
    difficulty: 3,
    total_questions: 2,
    answered_count: 2,
    completed: true,
    is_completed: true,
    started_at: "2026-11-20T10:00:00Z",
    completed_at: "2026-11-20T10:15:00Z",
    has_resume: false,
  },
  average_score: 62,
  content_quality_score: 62,
  completion_rate: 100,
  duration_minutes: 15,
  strengths: ["Clear structure"],
  improvements: ["Deepen PostgreSQL indexing knowledge"],
  overall_tip: "Focus on database indexing.",
  resources: ["PostgreSQL Documentation"],
  answers: [],
};

const SAMPLE_ROADMAP = {
  id: 10,
  session_id: 42,
  skill_gaps_json: [
    {
      concept: "Database Indexing",
      subject: "TECH",
      priority: "High",
      avg_score: 45,
      demonstrated_weaknesses: ["Average score of 45% across 1 interaction(s)."],
      improvement_opportunities: [],
    },
  ],
  roadmap_json: {
    title: "Personalized Backend Engineer Learning Roadmap",
    overview: "Targeted plan focusing on database indexing fundamentals.",
    estimated_hours: 6,
    learning_steps: [
      {
        order: 1,
        concept: "Database Indexing",
        subject: "Databases",
        priority: "High",
        why_needed: "Low score on B-tree indexing trade-offs.",
        learning_objectives: ["Understand B-tree vs hash index trade-offs"],
        how_to_learn: "Read PostgreSQL index internals and run EXPLAIN ANALYZE.",
        practical_example: "CREATE INDEX idx_orders_user_id ON orders(user_id);",
        exercise: "Benchmark a 100k-row query before and after adding a composite index.",
        interview_questions: ["When can an index hurt write throughput?"],
        resources: ["PostgreSQL Documentation — Indexes"],
        expected_outcome: "Confidently explain index selection and write amplification.",
      },
    ],
  },
};

describe("Dynamic Learning Roadmap Frontend Integration", () => {
  beforeEach(() => {
    tokenStorage.clearTokens();
    vi.restoreAllMocks();
  });

  it("shows Generate Learning Roadmap on Summary when none exists, prevents duplicate clicks, handles error/retry, and navigates", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionSummary").mockResolvedValue(SAMPLE_SUMMARY);
    vi.spyOn(sessionsApi, "fetchLearningRoadmap").mockRejectedValueOnce({
      response: { status: 404, data: { detail: "Not generated yet." } },
    });

    let rejectFirst;
    const genSpy = vi
      .spyOn(sessionsApi, "generateLearningRoadmap")
      .mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            rejectFirst = reject;
          })
      )
      .mockResolvedValueOnce(SAMPLE_ROADMAP);

    renderRoute("/sessions/42/summary");

    const genBtn = await screen.findByRole("button", {
      name: /generate learning roadmap/i,
    });
    expect(
      screen.queryByRole("button", { name: /view learning roadmap/i })
    ).not.toBeInTheDocument();

    // Double-click while in flight must only trigger 1 API call
    await user.click(genBtn);
    await user.click(genBtn);
    expect(genSpy).toHaveBeenCalledTimes(1);
    expect(genBtn).toBeDisabled();

    // Error shows Retry
    rejectFirst(new Error("Network Error"));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /unable to reach the mockmate server/i
    );

    await user.click(screen.getByRole("button", { name: /^retry$/i }));
    await waitFor(() => expect(genSpy).toHaveBeenCalledTimes(2));
    expect(genSpy).toHaveBeenLastCalledWith(42, { regenerate: false });

    // Navigates to /sessions/42/learning-roadmap and renders roadmap
    expect(
      await screen.findByRole("heading", {
        name: /personalized backend engineer learning roadmap/i,
      })
    ).toBeInTheDocument();
  });

  it("shows View Learning Roadmap on Summary when roadmap already exists and navigates without calling POST", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionSummary").mockResolvedValue(SAMPLE_SUMMARY);
    vi.spyOn(sessionsApi, "fetchLearningRoadmap").mockResolvedValue(SAMPLE_ROADMAP);
    const genSpy = vi.spyOn(sessionsApi, "generateLearningRoadmap");

    renderRoute("/sessions/42/summary");

    const viewLink = await screen.findByRole("link", {
      name: /view learning roadmap/i,
    });
    expect(viewLink).toHaveAttribute("href", "/sessions/42/learning-roadmap");

    await user.click(viewLink);

    expect(
      await screen.findByRole("heading", {
        name: /personalized backend engineer learning roadmap/i,
      })
    ).toBeInTheDocument();
    expect(genSpy).not.toHaveBeenCalled();
  });

  it("renders full roadmap details, supports explicit regeneration, and navigates back to summary", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi
      .spyOn(sessionsApi, "fetchLearningRoadmap")
      .mockResolvedValueOnce(SAMPLE_ROADMAP);

    const updatedRoadmap = {
      ...SAMPLE_ROADMAP,
      roadmap_json: {
        ...SAMPLE_ROADMAP.roadmap_json,
        title: "Regenerated Backend Roadmap v2",
        estimated_hours: 8,
      },
    };
    const genSpy = vi
      .spyOn(sessionsApi, "generateLearningRoadmap")
      .mockResolvedValueOnce(updatedRoadmap);

    renderRoute("/sessions/42/learning-roadmap");

    // Loads via GET without auto-regenerating
    expect(
      await screen.findByRole("heading", {
        name: /personalized backend engineer learning roadmap/i,
      })
    ).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith("42");
    expect(genSpy).not.toHaveBeenCalled();

    // Renders all required step sections & priority
    expect(screen.getByText("Est. 6 hrs")).toBeInTheDocument();
    expect(screen.getAllByText("High Priority").length).toBeGreaterThan(0);
    expect(screen.getByText(/low score on b-tree indexing trade-offs/i)).toBeInTheDocument();
    expect(screen.getByText(/understand b-tree vs hash index trade-offs/i)).toBeInTheDocument();
    expect(screen.getByText(/read postgresql index internals/i)).toBeInTheDocument();
    expect(screen.getByText(/create index idx_orders_user_id/i)).toBeInTheDocument();
    expect(screen.getByText(/benchmark a 100k-row query/i)).toBeInTheDocument();
    expect(screen.getByText(/when can an index hurt write throughput/i)).toBeInTheDocument();
    expect(screen.getByText(/postgresql documentation — indexes/i)).toBeInTheDocument();
    expect(screen.getByText(/confidently explain index selection/i)).toBeInTheDocument();

    // Explicit regeneration
    await user.click(screen.getByRole("button", { name: /regenerate roadmap/i }));
    await waitFor(() =>
      expect(genSpy).toHaveBeenCalledWith("42", { regenerate: true })
    );
    expect(
      await screen.findByRole("heading", { name: /regenerated backend roadmap v2/i })
    ).toBeInTheDocument();

    // Back to Summary link
    const backLink = screen.getByRole("link", { name: /back to interview summary/i });
    expect(backLink).toHaveAttribute("href", "/sessions/42/summary");
  });

  it("handles missing (404) roadmap and API failure states on LearningRoadmapPage", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchLearningRoadmap")
      .mockRejectedValueOnce({ response: { status: 500, data: { detail: "Server error" } } })
      .mockRejectedValueOnce({ response: { status: 404, data: { detail: "Not found" } } });
    const genSpy = vi
      .spyOn(sessionsApi, "generateLearningRoadmap")
      .mockResolvedValueOnce(SAMPLE_ROADMAP);

    renderRoute("/sessions/42/learning-roadmap");

    expect(
      await screen.findByRole("heading", { name: /could not load learning roadmap/i })
    ).toBeInTheDocument();

    // Retry hits 404 -> shows missing state with Generate CTA
    await user.click(screen.getByRole("button", { name: /^retry$/i }));
    expect(
      await screen.findByRole("heading", { name: /no learning roadmap generated yet/i })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate learning roadmap/i }));
    await waitFor(() =>
      expect(genSpy).toHaveBeenCalledWith("42", { regenerate: false })
    );
    expect(
      await screen.findByRole("heading", {
        name: /personalized backend engineer learning roadmap/i,
      })
    ).toBeInTheDocument();
  });
});

