import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import * as authApi from "../api/auth.api.js";
import * as resumesApi from "../api/resumes.api.js";
import * as sessionsApi from "../api/sessions.api.js";
import * as liveAvatarService from "../services/liveAvatarService.js";
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

const ADAPTIVE_SESSION = {
  id: 77,
  role: "tech",
  job_role: "Python Engineer",
  difficulty: 3,
  total_questions: 1,
  max_main_questions: 2,
  main_questions_count: 1,
  answered_count: 0,
  current_index: 1,
  state: "adaptive",
  completed: false,
  is_completed: false,
  has_resume: false,
  has_job_description: false,
};

const ADAPTIVE_Q1 = {
  has_next_question: true,
  session_id: 77,
  current_index: 1,
  total_questions: 1,
  answer_id: 701,
  question_kind: "main",
  question: {
    id: 8001,
    text: "Main Q1: Explain database indexing.",
    role: "tech",
    difficulty: 3,
  },
};

describe("Adaptive Interview Frontend Integration", () => {
  beforeEach(() => {
    tokenStorage.clearTokens();
    liveAvatarService.setLiveAvatarSessionFactory(null);
    vi.restoreAllMocks();
    Object.defineProperty(window, "speechSynthesis", {
      value: {
        speak: vi.fn(),
        cancel: vi.fn(),
        pause: vi.fn(),
        resume: vi.fn(),
        getVoices: () => [],
        onvoiceschanged: null,
      },
      configurable: true,
      writable: true,
    });
  });

  it("shows Adaptive mode in setup, sends exact payload, and navigates to workspace", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue([]);
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(ADAPTIVE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(ADAPTIVE_Q1);
    const createAdaptiveSpy = vi
      .spyOn(sessionsApi, "createAdaptiveSession")
      .mockResolvedValueOnce({
        message: "Adaptive interview session created successfully.",
        created_questions: 1,
        session: ADAPTIVE_SESSION,
        next_question: ADAPTIVE_Q1.question,
        next_question_kind: "main",
      });

    renderRoute("/sessions/new");
    await screen.findByRole("heading", { name: /start a new interview/i });

    const adaptiveCard = screen.getByRole("button", { name: /adaptive interview/i });
    expect(adaptiveCard).toBeInTheDocument();
    await user.click(adaptiveCard);

    await user.selectOptions(screen.getByLabelText(/interview focus/i), "tech");
    const roleInput = screen.getByLabelText(/target job role/i);
    await user.clear(roleInput);
    await user.type(roleInput, "Python Engineer");
    await user.selectOptions(screen.getByLabelText(/difficulty level/i), "3");
    const countInput = screen.getByLabelText(/number of main questions/i);
    await user.clear(countInput);
    await user.type(countInput, "2");

    await user.click(screen.getByRole("button", { name: /start adaptive interview/i }));

    await waitFor(() => expect(createAdaptiveSpy).toHaveBeenCalledTimes(1));
    expect(createAdaptiveSpy).toHaveBeenCalledWith({
      role: "tech",
      job_role: "Python Engineer",
      difficulty: 3,
      n_questions: 2,
    });

    expect(
      await screen.findByRole("heading", { name: /main q1: explain database indexing/i })
    ).toBeInTheDocument();
  });

  it("handles adaptive main -> follow-up -> next_main -> completed and opens Session Summary without mid-interview feedback", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(ADAPTIVE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(ADAPTIVE_Q1);
    const summarySpy = vi.spyOn(sessionsApi, "fetchSessionSummary").mockResolvedValue({
      session: { ...ADAPTIVE_SESSION, completed: true, is_completed: true, total_questions: 3 },
      average_score: 75,
      content_quality_score: 75,
      completion_rate: 100,
      duration_minutes: 3,
      strengths: ["Good fundamentals"],
      improvements: [],
      overall_tip: "Keep practicing.",
      resources: [],
      answers: [
        {
          id: 701,
          index: 1,
          parent_answer_id: null,
          is_follow_up: false,
          question: ADAPTIVE_Q1.question,
          answer_text: "Indexes speed up reads.",
          score: 55,
          feedback: "Good start.",
          improvement_tips: [],
          expected_answer: "B-tree details",
          processed: true,
          has_audio: false,
        },
        {
          id: 702,
          index: 2,
          parent_answer_id: 701,
          is_follow_up: true,
          question: { id: 8002, text: "Follow-up Q1: When do indexes hurt writes?", role: "tech", difficulty: 3 },
          answer_text: "On frequent inserts.",
          score: 80,
          feedback: "Solid.",
          improvement_tips: [],
          expected_answer: "Write amplification",
          processed: true,
          has_audio: false,
        },
      ],
    });

    const adaptiveSubmitSpy = vi
      .spyOn(sessionsApi, "submitAdaptiveAnswer")
      .mockResolvedValueOnce({
        message: "Answer submitted and evaluated successfully.",
        session_id: 77,
        is_session_completed: false,
        answer: { id: 701, index: 1, answer_text: "Indexes speed up reads.", score: 55, feedback: "Detailed secret feedback", processed: true },
        next_question: { id: 8002, text: "Follow-up Q1: When do indexes hurt writes?", role: "tech", difficulty: 3 },
        next_question_kind: "follow_up",
        main_questions_count: 1,
        max_main_questions: 2,
        total_interactions: 2,
      })
      .mockResolvedValueOnce({
        message: "Answer submitted and evaluated successfully.",
        session_id: 77,
        is_session_completed: false,
        answer: { id: 702, index: 2, answer_text: "On frequent inserts.", score: 80, feedback: "Good.", processed: true },
        next_question: { id: 8003, text: "Main Q2: Explain ACID transactions.", role: "tech", difficulty: 4 },
        next_question_kind: "main",
        main_questions_count: 2,
        max_main_questions: 2,
        total_interactions: 3,
      })
      .mockResolvedValueOnce({
        message: "Answer submitted and evaluated successfully.",
        session_id: 77,
        is_session_completed: true,
        answer: { id: 703, index: 3, answer_text: "Atomicity, consistency, isolation, durability.", score: 90, feedback: "Great.", processed: true },
        next_question: null,
        next_question_kind: null,
        main_questions_count: 2,
        max_main_questions: 2,
        total_interactions: 3,
      });

    renderRoute("/sessions/77/interview");

    expect(
      await screen.findByRole("heading", { name: /main q1: explain database indexing/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Adaptive")).toBeInTheDocument();
    expect(screen.getByText("Main 1 / 2")).toBeInTheDocument();
    expect(screen.getByText("Main Question")).toBeInTheDocument();

    // 1. Submit Main Q1 -> Follow-up Q1 appears, no detailed feedback displayed mid-interview
    const answerBox = screen.getByLabelText(/your answer/i, { selector: "textarea" });
    await user.type(answerBox, "Indexes speed up reads.");
    await user.click(screen.getByRole("button", { name: /submit answer/i }));

    expect(
      await screen.findByRole("heading", { name: /follow-up q1: when do indexes hurt writes/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Follow-up")).toBeInTheDocument();
    expect(screen.getByText("1 / 2 Interactions")).toBeInTheDocument();
    expect(screen.queryByText(/detailed secret feedback/i)).not.toBeInTheDocument();

    // 2. Submit Follow-up Q1 -> Advances to Main Q2
    await user.type(screen.getByLabelText(/your answer/i, { selector: "textarea" }), "On frequent inserts.");
    await user.click(screen.getByRole("button", { name: /submit answer/i }));

    expect(
      await screen.findByRole("heading", { name: /main q2: explain acid transactions/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Main 2 / 2")).toBeInTheDocument();
    expect(screen.getByText("Main Question")).toBeInTheDocument();

    // 3. Submit Main Q2 -> Session completes and navigates to Session Summary
    await user.type(screen.getByLabelText(/your answer/i, { selector: "textarea" }), "ACID guarantees.");
    await user.click(screen.getByRole("button", { name: /submit answer/i }));

    await waitFor(() => expect(adaptiveSubmitSpy).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(summarySpy).toHaveBeenCalledWith("77"));
    expect(await screen.findByText(/performance overview/i)).toBeInTheDocument();
  });

  it("handles adaptive skip and refresh restoration of a follow-up question", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue({
      ...ADAPTIVE_SESSION,
      total_questions: 2,
      answered_count: 1,
      current_index: 2,
    });
    // Refreshing directly on a follow-up question restores Follow-up badge and prompt
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue({
      has_next_question: true,
      session_id: 77,
      current_index: 2,
      total_questions: 2,
      answer_id: 702,
      question_kind: "follow_up",
      question: { id: 8002, text: "Follow-up Q1: Restored after refresh", role: "tech", difficulty: 3 },
    });
    const adaptiveSkipSpy = vi.spyOn(sessionsApi, "skipAdaptiveQuestion").mockResolvedValueOnce({
      message: "Question skipped successfully.",
      session_id: 77,
      is_session_completed: false,
      answer: { id: 702, index: 2, answer_text: "[Skipped]", score: 0, processed: true },
      next_question: { id: 8003, text: "Main Q2: After skip", role: "tech", difficulty: 3 },
      next_question_kind: "main",
      main_questions_count: 2,
      max_main_questions: 2,
      total_interactions: 3,
    });

    renderRoute("/sessions/77/interview");

    expect(
      await screen.findByRole("heading", { name: /follow-up q1: restored after refresh/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Follow-up")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^skip question$/i }));
    const dialog = screen.getByRole("dialog", { name: /skip this question/i });
    await user.click(within(dialog).getByRole("button", { name: /skip question/i }));

    await waitFor(() => expect(adaptiveSkipSpy).toHaveBeenCalledWith("77", { answerId: 702 }));
    expect(
      await screen.findByRole("heading", { name: /main q2: after skip/i })
    ).toBeInTheDocument();
  });
});

