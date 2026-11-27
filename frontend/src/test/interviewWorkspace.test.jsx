import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import * as authApi from "../api/auth.api.js";
import * as sessionsApi from "../api/sessions.api.js";
import * as liveAvatarService from "../services/liveAvatarService.js";
import { tokenStorage } from "../utils/tokenStorage.js";

const SAMPLE_SESSION = {
  id: 42,
  role: "tech",
  job_role: "Senior Python Engineer",
  difficulty: 4,
  total_questions: 3,
  answered_count: 0,
  current_index: 1,
  state: "in_progress",
  completed: false,
  is_completed: false,
  has_resume: true,
  has_job_description: true,
  resume_id: 10,
  resume_title: "Alex Python CV",
};

const QUESTION_1 = {
  has_next_question: true,
  session_id: 42,
  current_index: 1,
  total_questions: 3,
  answer_id: 501,
  question: {
    id: 9001,
    text: "Explain how Django transactions and atomic blocks work.",
    role: "tech",
    difficulty: 4,
  },
};

const QUESTION_2 = {
  id: 9002,
  text: "How do you optimize slow PostgreSQL queries in production?",
  role: "tech",
  difficulty: 4,
};

function installMockSpeechSynthesis() {
  const cancelSpy = vi.fn();
  const speakSpy = vi.fn((utterance) => {
    utterance.onstart?.();
  });
  const pauseSpy = vi.fn();
  const resumeSpy = vi.fn();

  class MockUtterance {
    constructor(text) {
      this.text = text;
      this.volume = 1;
      this.voice = null;
    }
  }

  Object.defineProperty(window, "SpeechSynthesisUtterance", {
    value: MockUtterance,
    configurable: true,
    writable: true,
  });

  Object.defineProperty(window, "speechSynthesis", {
    value: {
      speak: speakSpy,
      cancel: cancelSpy,
      pause: pauseSpy,
      resume: resumeSpy,
      getVoices: () => [
        { voiceURI: "en-US-1", name: "Studio English", lang: "en-US" },
      ],
      onvoiceschanged: null,
    },
    configurable: true,
    writable: true,
  });

  return { speakSpy, cancelSpy, pauseSpy, resumeSpy };
}

function installMockMediaRecorder() {
  const stopMicTrackSpy = vi.fn();
  const fakeMicStream = {
    getTracks: () => [{ stop: stopMicTrackSpy }],
  };

  class MockMediaRecorder {
    static isTypeSupported(mime) {
      return mime === "audio/webm;codecs=opus" || mime === "audio/webm";
    }

    constructor(stream, options = {}) {
      this.stream = stream;
      this.mimeType = options.mimeType || "audio/webm";
      this.state = "inactive";
      this.ondataavailable = null;
      this.onstop = null;
      this.onerror = null;
    }

    start() {
      this.state = "recording";
      if (this.ondataavailable) {
        this.ondataavailable({
          data: new Blob(["recorded-audio-bytes"], { type: this.mimeType }),
        });
      }
    }

    pause() {
      this.state = "paused";
    }

    resume() {
      this.state = "recording";
    }

    stop() {
      this.state = "inactive";
      if (this.onstop) {
        this.onstop();
      }
    }
  }

  Object.defineProperty(window, "MediaRecorder", {
    value: MockMediaRecorder,
    configurable: true,
    writable: true,
  });

  URL.createObjectURL = vi.fn(() => "blob:http://localhost:5173/mock-audio");
  URL.revokeObjectURL = vi.fn();

  return { fakeMicStream, stopMicTrackSpy };
}

function renderWorkspace(sessionId = 42) {
  tokenStorage.setTokens({ access: "valid-access", refresh: "valid-refresh" });
  vi.spyOn(authApi, "fetchCurrentUser").mockResolvedValue({
    id: 1,
    username: "alexchen",
    email: "alex@example.com",
    first_name: "Alex",
    last_name: "Chen",
    user_type: "job_seeker",
    target_role: "Senior Python Engineer",
  });

  return render(
    <AuthProvider>
      <ToastProvider>
        <MemoryRouter initialEntries={[`/sessions/${sessionId}/interview`]}>
          <AppRoutes />
        </MemoryRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

describe("Live Interview Studio (/sessions/:id/interview)", () => {
  beforeEach(() => {
    tokenStorage.clearTokens();
    liveAvatarService.setLiveAvatarSessionFactory(null);
    vi.restoreAllMocks();
    installMockSpeechSynthesis();
  });

  it("loads session details, dominant AI interviewer stage, and exclusive answer mode dock", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);

    renderWorkspace(42);

    expect(
      await screen.findByRole("heading", {
        name: /explain how django transactions and atomic blocks work/i,
      })
    ).toBeInTheDocument();
    expect(screen.getByText("MockMate AI Interviewer")).toBeInTheDocument();
    expect(screen.getAllByText("Senior Python Engineer").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Question 1 of 3").length).toBeGreaterThan(0);
    expect(screen.getByText("0 / 3")).toBeInTheDocument();
    expect(screen.getByText("Alex Python CV")).toBeInTheDocument();

    // Text mode is active by default; voice recorder controls are NOT shown simultaneously
    expect(
      screen.getByLabelText(/your answer/i, { selector: "textarea" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /start recording/i })
    ).not.toBeInTheDocument();

    // Switching to Voice Answer hides the textarea and shows voice recording controls
    await user.click(screen.getByRole("tab", { name: /voice answer/i }));
    expect(
      screen.queryByLabelText(/your answer/i, { selector: "textarea" })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /start recording/i })
    ).toBeInTheDocument();
  });

  it("validates empty answers, submits a valid text answer, and advances to next question", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);

    const submitSpy = vi.spyOn(sessionsApi, "submitAnswer").mockResolvedValueOnce({
      message: "Answer submitted and evaluated successfully.",
      is_session_completed: false,
      answer: {
        id: 501,
        index: 1,
        answer_text: "transaction.atomic wraps operations in a database transaction.",
        score: 88,
        feedback: "Clear explanation of savepoints and rollback behavior.",
        processed: true,
        has_audio: false,
      },
      next_question: QUESTION_2,
    });

    renderWorkspace(42);
    await screen.findByRole("heading", {
      name: /explain how django transactions and atomic blocks work/i,
    });

    await user.click(screen.getByRole("button", { name: /submit answer/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /please enter your answer before submitting/i
    );
    expect(submitSpy).not.toHaveBeenCalled();

    const answerBox = screen.getByLabelText(/your answer/i, { selector: "textarea" });
    await user.type(
      answerBox,
      "transaction.atomic wraps operations in a database transaction."
    );
    await user.click(screen.getByRole("button", { name: /submit answer/i }));

    await waitFor(() => expect(submitSpy).toHaveBeenCalledTimes(1));
    expect(submitSpy).toHaveBeenCalledWith(
      "42",
      expect.objectContaining({
        answerId: 501,
        answerText: "transaction.atomic wraps operations in a database transaction.",
        audioBlob: null,
        audioFilename: "",
      })
    );

    expect(
      await screen.findByRole("heading", {
        name: /how do you optimize slow postgresql queries in production/i,
      })
    ).toBeInTheDocument();
    expect(answerBox).toHaveValue("");
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(
      screen.getByText(/clear explanation of savepoints and rollback behavior/i)
    ).toBeInTheDocument();
  });

  it("prevents duplicate submissions, disables End Interview while submitting, and preserves draft on failure", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);

    let rejectSubmit;
    const submitSpy = vi.spyOn(sessionsApi, "submitAnswer").mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          rejectSubmit = reject;
        })
    );

    renderWorkspace(42);
    const answerBox = await screen.findByLabelText(/your answer/i, {
      selector: "textarea",
    });

    await user.type(answerBox, "My important draft response that must not be lost");

    const submitBtn = screen.getByRole("button", { name: /submit answer/i });
    await user.click(submitBtn);
    await user.click(submitBtn);

    expect(submitSpy).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: /end interview/i })).toBeDisabled();

    rejectSubmit({
      response: {
        status: 503,
        data: { detail: "The server is temporarily busy processing your answer." },
      },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /temporarily busy processing your answer/i
    );
    expect(answerBox).toHaveValue("My important draft response that must not be lost");
  });

  it("records a voice answer, supports pause/resume/playback/re-record, uploads audio, and displays Whisper transcript", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);

    const { fakeMicStream, stopMicTrackSpy } = installMockMediaRecorder();
    const getUserMediaSpy = vi.fn().mockResolvedValue(fakeMicStream);
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: getUserMediaSpy },
      configurable: true,
    });

    const submitSpy = vi
      .spyOn(sessionsApi, "submitAnswer")
      .mockRejectedValueOnce({
        response: { status: 503, data: { detail: "Temporary upload error." } },
      })
      .mockResolvedValueOnce({
        message: "Answer submitted and evaluated successfully.",
        is_session_completed: false,
        answer: {
          id: 501,
          index: 1,
          answer_text: "We use atomic blocks to guarantee database consistency.",
          score: 91,
          feedback: "Strong voice explanation of atomicity.",
          improvement_tips: ["Mention select_for_update for row locking."],
          processed: true,
          has_audio: true,
        },
        next_question: QUESTION_2,
      });

    renderWorkspace(42);
    await screen.findByRole("heading", {
      name: /explain how django transactions and atomic blocks work/i,
    });

    await user.click(screen.getByRole("tab", { name: /voice answer/i }));
    expect(getUserMediaSpy).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /start recording/i }));
    expect(getUserMediaSpy).toHaveBeenCalledWith({ audio: true });
    expect(screen.getByText(/recording live audio/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /pause recording/i }));
    expect(screen.getByText(/recording paused/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /resume recording/i }));
    expect(screen.getByText(/recording live audio/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /stop recording/i }));
    expect(stopMicTrackSpy).toHaveBeenCalled();
    expect(
      screen.getByLabelText(/preview recorded voice answer/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /re-record/i }));
    expect(
      screen.queryByLabelText(/preview recorded voice answer/i)
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /start recording/i }));
    await user.click(screen.getByRole("button", { name: /stop recording/i }));
    expect(
      screen.getByLabelText(/preview recorded voice answer/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /submit answer/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /temporary upload error/i
    );
    expect(
      screen.getByLabelText(/preview recorded voice answer/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /submit answer/i }));
    await waitFor(() => expect(submitSpy).toHaveBeenCalledTimes(2));
    expect(submitSpy).toHaveBeenLastCalledWith(
      "42",
      expect.objectContaining({
        answerId: 501,
        audioBlob: expect.any(Blob),
        audioFilename: "candidate-answer.webm",
      })
    );

    expect(
      await screen.findByText(/recognized speech transcript/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/we use atomic blocks to guarantee database consistency/i)
    ).toBeInTheDocument();
  });

  it("handles microphone permission denial cleanly", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);

    installMockMediaRecorder();
    const deniedErr = new Error("Permission denied");
    deniedErr.name = "NotAllowedError";
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: vi.fn().mockRejectedValue(deniedErr) },
      configurable: true,
    });

    renderWorkspace(42);
    await screen.findByRole("heading", {
      name: /explain how django transactions and atomic blocks work/i,
    });

    await user.click(screen.getByRole("tab", { name: /voice answer/i }));
    await user.click(screen.getByRole("button", { name: /start recording/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /microphone permission was denied/i
    );
  });

  it("narrates question via SpeechSynthesis, synchronizes avatar state, prevents overlap on replay, and stops on unmount", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);

    const { speakSpy, cancelSpy } = installMockSpeechSynthesis();

    const { unmount } = renderWorkspace(42);
    await screen.findByRole("heading", {
      name: /explain how django transactions and atomic blocks work/i,
    });

    const avatarStage = screen.getByLabelText(/ai interviewer stage/i);
    expect(avatarStage).toHaveAttribute("data-avatar-state", "idle");

    await user.click(screen.getByRole("button", { name: /read question aloud/i }));
    expect(speakSpy).toHaveBeenCalledTimes(1);
    expect(avatarStage).toHaveAttribute("data-avatar-state", "speaking");
    expect(
      screen.getByLabelText(/interviewer question captions/i)
    ).toHaveTextContent(/explain how django transactions/i);

    const cancelCountBeforeReplay = cancelSpy.mock.calls.length;
    await user.click(screen.getByRole("button", { name: /repeat question/i }));
    expect(cancelSpy.mock.calls.length).toBeGreaterThan(cancelCountBeforeReplay);
    expect(speakSpy).toHaveBeenCalledTimes(2);

    const cancelCountBeforeUnmount = cancelSpy.mock.calls.length;
    unmount();
    expect(cancelSpy.mock.calls.length).toBeGreaterThan(cancelCountBeforeUnmount);
  });

  it("connects opt-in LiveAvatar WebRTC session, speaks backend question without browser TTS overlap, and disconnects on unmount", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);
    const { speakSpy } = installMockSpeechSynthesis();

    const startSpy = vi.fn().mockResolvedValue(undefined);
    const attachSpy = vi.fn();
    const repeatSpy = vi.fn().mockResolvedValue(undefined);
    const interruptSpy = vi.fn().mockResolvedValue(undefined);
    const stopSpy = vi.fn().mockResolvedValue(undefined);

    vi.spyOn(liveAvatarService, "createAndStartLiveAvatarSession").mockImplementation(
      async ({ videoElement, onSpeakingChange }) => {
        await startSpy();
        attachSpy(videoElement);
        return {
          avatarName: "Sarah",
          provider: "heygen_liveavatar",
          async speakQuestion(text) {
            onSpeakingChange?.(true);
            await repeatSpy(text);
          },
          async interrupt() {
            onSpeakingChange?.(false);
            await interruptSpy();
          },
          async stop() {
            onSpeakingChange?.(false);
            await stopSpy();
          },
        };
      }
    );

    const { unmount } = renderWorkspace(42);
    await screen.findByRole("heading", {
      name: /explain how django transactions and atomic blocks work/i,
    });

    // Does NOT connect automatically on page load
    expect(startSpy).not.toHaveBeenCalled();

    // Candidate explicitly clicks Connect Live Avatar
    await user.click(screen.getByRole("button", { name: /connect live avatar/i }));
    await waitFor(() => expect(startSpy).toHaveBeenCalledTimes(1));
    expect(attachSpy).toHaveBeenCalledWith(expect.any(HTMLVideoElement));

    // Read question aloud -> uses LiveAvatar repeat() and does NOT call browser speechSynthesis.speak()
    await user.click(screen.getByRole("button", { name: /read question aloud/i }));
    expect(repeatSpy).toHaveBeenCalledWith(
      "Explain how Django transactions and atomic blocks work."
    );
    expect(speakSpy).not.toHaveBeenCalled();

    // Unmount disconnects the avatar session cleanly
    unmount();
    expect(stopSpy).toHaveBeenCalledTimes(1);
  });

  it("confirms and skips a question, and handles skip API failure gracefully", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);

    const skipSpy = vi
      .spyOn(sessionsApi, "skipQuestion")
      .mockRejectedValueOnce({
        response: { status: 503, data: { detail: "The server is temporarily busy." } },
      })
      .mockResolvedValueOnce({
        message: "Question skipped successfully.",
        is_session_completed: false,
        answer: { id: 501, index: 1, score: 0, feedback: "Question skipped.", processed: true },
        next_question: QUESTION_2,
      });

    renderWorkspace(42);
    await screen.findByRole("heading", {
      name: /explain how django transactions and atomic blocks work/i,
    });

    await user.click(screen.getByRole("button", { name: /^skip question$/i }));
    let dialog = screen.getByRole("dialog", { name: /skip this question/i });
    await user.click(within(dialog).getByRole("button", { name: /skip question/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/temporarily busy/i);
    expect(
      screen.getByRole("heading", {
        name: /explain how django transactions and atomic blocks work/i,
      })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^skip question$/i }));
    dialog = screen.getByRole("dialog", { name: /skip this question/i });
    await user.click(within(dialog).getByRole("button", { name: /skip question/i }));

    expect(skipSpy).toHaveBeenCalledTimes(2);
    expect(
      await screen.findByRole("heading", {
        name: /how do you optimize slow postgresql queries in production/i,
      })
    ).toBeInTheDocument();
  });

  it("ends the interview with confirmation and navigates to the summary page", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);
    const endSpy = vi.spyOn(sessionsApi, "endSession").mockResolvedValueOnce({
      message: "Interview session ended successfully.",
      session: { ...SAMPLE_SESSION, completed: true, is_completed: true },
    });
    const summarySpy = vi.spyOn(sessionsApi, "fetchSessionSummary").mockResolvedValueOnce({
      session: { ...SAMPLE_SESSION, completed: true, is_completed: true },
      average_score: 82,
      content_quality_score: 82,
      completion_rate: 33,
      duration_minutes: 4,
      strengths: ["Clear explanation of atomic transactions."],
      improvements: ["Include concrete rollback examples."],
      overall_tip: "Keep structuring answers around real-world trade-offs.",
      resources: [],
      answers: [
        {
          id: 501,
          index: 1,
          question: QUESTION_1.question,
          answer_text: "Atomic blocks wrap DB operations in a single transaction.",
          score: 82,
          feedback: "Solid explanation.",
          improvement_tips: [],
          expected_answer: "Explain savepoints and rollback semantics.",
          processed: true,
          has_audio: false,
        },
      ],
    });
    vi.spyOn(sessionsApi, "fetchLearningRoadmap").mockRejectedValueOnce({
      response: { status: 404, data: { detail: "Not found" } },
    });

    renderWorkspace(42);
    await screen.findByRole("heading", {
      name: /explain how django transactions and atomic blocks work/i,
    });

    await user.click(screen.getByRole("button", { name: /end interview/i }));
    const dialog = screen.getByRole("dialog", { name: /end interview session/i });
    await user.click(within(dialog).getByRole("button", { name: /end interview/i }));

    await waitFor(() => expect(endSpy).toHaveBeenCalledWith("42"));
    await waitFor(() => expect(summarySpy).toHaveBeenCalledWith("42"));
    expect(
      await screen.findByRole("heading", { name: /performance overview/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /download pdf report/i })
    ).toBeInTheDocument();
  });

  it("handles invalid or inaccessible session IDs with error and retry", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail")
      .mockRejectedValueOnce({
        response: { status: 404, data: { detail: "Not found." } },
      })
      .mockResolvedValueOnce(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion")
      .mockRejectedValueOnce({
        response: { status: 404, data: { detail: "Not found." } },
      })
      .mockResolvedValueOnce(QUESTION_1);

    renderWorkspace(999);

    expect(
      await screen.findByRole("heading", { name: /unable to load interview session/i })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /retry/i }));

    expect(
      await screen.findByRole("heading", {
        name: /explain how django transactions and atomic blocks work/i,
      })
    ).toBeInTheDocument();
  });

  it("requests camera only on explicit user action and stops tracks on disable and unmount", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessionDetail").mockResolvedValue(SAMPLE_SESSION);
    vi.spyOn(sessionsApi, "fetchNextQuestion").mockResolvedValue(QUESTION_1);

    const stopTrackSpy = vi.fn();
    const fakeStream = {
      getTracks: () => [{ stop: stopTrackSpy }],
    };
    const getUserMediaSpy = vi.fn().mockResolvedValue(fakeStream);
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: getUserMediaSpy },
      configurable: true,
    });

    const { unmount } = renderWorkspace(42);
    await screen.findByRole("heading", {
      name: /explain how django transactions and atomic blocks work/i,
    });

    expect(getUserMediaSpy).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /enable camera/i }));
    await waitFor(() => expect(getUserMediaSpy).toHaveBeenCalledTimes(1));

    await user.click(await screen.findByRole("button", { name: /disable camera/i }));
    expect(stopTrackSpy).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: /enable camera/i }));
    await screen.findByRole("button", { name: /disable camera/i });
    unmount();
    expect(stopTrackSpy).toHaveBeenCalledTimes(2);
  });
});
