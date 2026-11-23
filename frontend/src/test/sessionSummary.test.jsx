import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SessionSummaryPage } from "../pages/SessionSummaryPage.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import * as sessionsApi from "../api/sessions.api.js";

const SAMPLE_SUMMARY = {
  session: {
    id: 42,
    role: "tech",
    job_role: "Staff Backend Engineer",
    difficulty: 4,
    total_questions: 3,
    answered_count: 2,
    current_index: 3,
    state: "completed",
    completed: true,
    is_completed: true,
    total_score: 84.0,
    duration: 18,
    started_at: "2026-11-20T10:00:00Z",
    completed_at: "2026-11-20T10:18:00Z",
    has_resume: true,
    has_job_description: true,
    resume_id: 12,
    resume_title: "Alex_Staff_CV.pdf",
    job_description: "Staff backend engineer with distributed systems experience.",
  },
  avg: 84.0,
  average_score: 84.0,
  content_quality_score: 88.5,
  completion_rate: 67,
  duration: 18,
  duration_minutes: 18,
  strengths: [
    "Comprehensive explanation of distributed transactions and 2PC failure modes.",
    "Strong technical vocabulary and precise database isolation level trade-offs.",
  ],
  improvements: [
    "Elaborate more on observability and tracing when discussing production debugging.",
    "State concrete latency metrics rather than general latency statements.",
  ],
  overall_tip:
    "Ground architectural answers in business trade-offs and latency budget requirements.",
  resources: [
    "Designing Data-Intensive Applications (DDIA)",
    "Distributed Consensus Protocols & Raft",
    "PostgreSQL Concurrency & MVCC Deep Dive",
  ],
  resume_summary: {
    resume_title: "Alex_Staff_CV.pdf",
    avg_consistency_score: 18.5,
    consistency_pct: 92,
    supported_count: 4,
    contradictions_count: 0,
    missed_count: 1,
  },
  video_summary: {
    confidence_score: 86.5,
    engagement_level: "Excellent",
    presence_pct: 98.2,
    eye_contact_pct: 82.4,
    movement_pct: 12.0,
    tips: ["Great confidence and engagement throughout the interview."],
  },
  video_ai_feedback: {
    summary: "Clear posture, steady eye contact, and articulate cadence.",
    strengths: ["Maintained continuous eye contact with interviewer."],
    improvements: ["Keep steady breathing during complex reasoning."],
  },
  answers: [
    {
      id: 501,
      index: 1,
      question: {
        id: 901,
        text: "How do you guarantee atomicity and idempotency in distributed payment microservices?",
        role: "tech",
        difficulty: 4,
      },
      answer_text:
        "We implement the Transactional Outbox pattern paired with idempotent consumer keys stored in Redis.",
      score: 92.0,
      feedback:
        "Excellent architectural grasp. Good mention of transactional outbox and Redis idempotency keys.",
      improvement_tips: [
        "Mention message delivery semantics like at-least-once delivery.",
      ],
      resume_grounding: {
        alignment_level: "high",
        consistency_score: 19,
        supported_claims: ["Engineered payment processing pipeline processing 10k RPS."],
        missed_resume_points: [],
        contradictions: [],
      },
      expected_answer:
        "Key concepts include idempotency keys, transactional outbox pattern, distributed consensus or saga orchestration, and deduplication tables.",
      processed: true,
      has_audio: true,
    },
    {
      id: 502,
      index: 2,
      question: {
        id: 902,
        text: "Explain the trade-offs between optimistic locking and pessimistic locking in high-throughput workloads.",
        role: "tech",
        difficulty: 4,
      },
      answer_text:
        "Optimistic locking uses a version column without holding database locks, which excels when collision rates are low.",
      score: 85.0,
      feedback:
        "Clear definition. Accurately identified that high collision frequency causes excessive rollbacks in optimistic concurrency.",
      improvement_tips: "Discuss exponential backoff retries on conflict exceptions.",
      resume_grounding: null,
      expected_answer:
        "Optimistic concurrency control assumes conflicts are rare, checking versions at commit. Pessimistic concurrency locks records immediately.",
      processed: true,
      has_audio: false,
    },
    {
      id: 503,
      index: 3,
      question: {
        id: 903,
        text: "How would you design a distributed rate limiter that scales to millions of users across multi-region clusters?",
        role: "tech",
        difficulty: 5,
      },
      answer_text: "[Skipped]",
      score: 0,
      feedback: "Candidate chose to skip this question.",
      improvement_tips: [],
      resume_grounding: null,
      expected_answer:
        "Use sliding window log or token bucket algorithms in local Redis instances with batched global synchronization.",
      processed: true,
      has_audio: false,
    },
  ],
};

function renderSummaryPage(sessionId = "42") {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${sessionId}/summary`]}>
      <ToastProvider>
        <Routes>
          <Route path="/sessions/:id/summary" element={<SessionSummaryPage />} />
          <Route path="/sessions/:id/interview" element={<div>Interview Workspace Stub</div>} />
          <Route path="/dashboard" element={<div>Dashboard Stub</div>} />
          <Route path="/sessions/new" element={<div>New Session Stub</div>} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );
}

describe("SessionSummaryPage (/sessions/:id/summary)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads and displays full executive performance report with real backend data", async () => {
    vi.spyOn(sessionsApi, "fetchSessionSummary").mockResolvedValueOnce(SAMPLE_SUMMARY);

    renderSummaryPage("42");

    // Initially displays skeleton loader
    expect(screen.getByLabelText(/loading interview performance report/i)).toBeInTheDocument();

    // Await completed report header
    expect(await screen.findByText("Staff Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText(/Session Completed/i)).toBeInTheDocument();
    expect(screen.getByText(/18 minutes duration/i)).toBeInTheDocument();
    expect(screen.getByText(/Difficulty: Level 4\/5/i)).toBeInTheDocument();

    // Verify Performance Overview metrics
    expect(screen.getByText(/Overall Session Score/i)).toBeInTheDocument();
    expect(screen.getAllByText("84").length).toBeGreaterThan(0);
    expect(screen.getByText("89")).toBeInTheDocument(); // Answer Quality Score rounded from 88.5
    expect(screen.getByText("67%")).toBeInTheDocument(); // Completion rate

    // Verify AI insights
    expect(
      screen.getByText(/Ground architectural answers in business trade-offs/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Comprehensive explanation of distributed transactions/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Elaborate more on observability and tracing/i)
    ).toBeInTheDocument();

    // Verify Resume & Video telemetry
    expect(screen.getByText(/92% Match/i)).toBeInTheDocument();
    expect(screen.getByText(/Alex_Staff_CV\.pdf/i)).toBeInTheDocument();
    expect(screen.getByText(/86\.5% Confidence/i)).toBeInTheDocument();

    // Verify Improvement Plan Resources
    expect(
      screen.getByText(/Designing Data-Intensive Applications \(DDIA\)/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Distributed Consensus Protocols & Raft/i)).toBeInTheDocument();

    // Verify Question-by-Question study review
    expect(screen.getByText(/Question-by-Question Study Review/i)).toBeInTheDocument();
    expect(screen.getByText(/Question 1/i)).toBeInTheDocument();
    expect(
      screen.getAllByText(/How do you guarantee atomicity and idempotency/i)[0]
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Explain the trade-offs between optimistic locking/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/How would you design a distributed rate limiter/i)
    ).toBeInTheDocument();
  });

  it("filters questions by answered and skipped tabs", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionSummary").mockResolvedValueOnce(SAMPLE_SUMMARY);

    renderSummaryPage("42");

    expect(await screen.findByText("Staff Backend Engineer")).toBeInTheDocument();

    // Click 'Skipped (1)' filter
    const skippedButton = screen.getByRole("button", { name: /^Skipped \(1\)$/i });
    await user.click(skippedButton);

    // Only skipped question should be visible
    expect(
      screen.getByText(/How would you design a distributed rate limiter/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/How do you guarantee atomicity and idempotency/i)
    ).not.toBeInTheDocument();

    // Click 'Answered (2)' filter
    const answeredButton = screen.getByRole("button", { name: /^Answered \(2\)$/i });
    await user.click(answeredButton);

    expect(
      screen.getAllByText(/How do you guarantee atomicity and idempotency/i)[0]
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Explain the trade-offs between optimistic locking/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/How would you design a distributed rate limiter/i)
    ).not.toBeInTheDocument();
  });

  it("triggers PDF report download when clicking download button", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionSummary").mockResolvedValueOnce(SAMPLE_SUMMARY);
    const triggerSpy = vi.spyOn(sessionsApi, "triggerReportDownload").mockResolvedValueOnce();

    renderSummaryPage("42");

    const downloadBtn = await screen.findByRole("button", { name: /Download PDF Report/i });
    expect(downloadBtn).toBeEnabled();

    await user.click(downloadBtn);

    expect(triggerSpy).toHaveBeenCalledWith(42);
    expect(await screen.findByText(/Report Downloaded/i)).toBeInTheDocument();
  });

  it("displays pending state when session is not yet completed", async () => {
    const incompleteError = {
      response: {
        status: 400,
        data: {
          detail: "Session performance summary is only available after interview completion.",
        },
      },
    };
    vi.spyOn(sessionsApi, "fetchSessionSummary").mockRejectedValueOnce(incompleteError);

    renderSummaryPage("42");

    expect(await screen.findByText(/Interview Session in Progress/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Performance summaries and downloadable PDF evaluations are generated/i)
    ).toBeInTheDocument();

    const returnBtn = screen.getByRole("button", { name: /Return to Active Interview/i });
    expect(returnBtn).toBeInTheDocument();
  });

  it("displays error card and allows retry when API fails", async () => {
    const user = userEvent.setup();
    const networkError = {
      message: "Network Error",
      response: { status: 500, data: { detail: "Internal Server Error" } },
    };
    const fetchSpy = vi
      .spyOn(sessionsApi, "fetchSessionSummary")
      .mockRejectedValueOnce(networkError)
      .mockResolvedValueOnce(SAMPLE_SUMMARY);

    renderSummaryPage("42");

    expect(await screen.findByText(/Could Not Load Report/i)).toBeInTheDocument();
    expect(screen.getByText(/Internal Server Error/i)).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: /Retry Loading/i });
    await user.click(retryBtn);

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("Staff Backend Engineer")).toBeInTheDocument();
  });

  it("displays API detail message on 404 not found", async () => {
    const notFoundError = {
      response: { status: 404, data: { detail: "No InterviewSession matches the given query." } },
    };
    vi.spyOn(sessionsApi, "fetchSessionSummary").mockRejectedValueOnce(notFoundError);

    renderSummaryPage("999");

    expect(await screen.findByText(/Could Not Load Report/i)).toBeInTheDocument();
    expect(
      screen.getByText(/No InterviewSession matches the given query\./i)
    ).toBeInTheDocument();
  });

  it("displays connection message when server is unreachable", async () => {
    const offlineError = { message: "Network Error" };
    vi.spyOn(sessionsApi, "fetchSessionSummary").mockRejectedValueOnce(offlineError);

    renderSummaryPage("42");

    expect(await screen.findByText(/Could Not Load Report/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Unable to reach the MockMate server/i)
    ).toBeInTheDocument();
  });
});

