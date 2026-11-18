import { render, screen, within } from "@testing-library/react";
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

function makeSessions(count) {
  const now = Date.now();
  return Array.from({ length: count }, (_, idx) => {
    const id = idx + 1;
    const daysAgo = idx * 3;
    return {
      id,
      role: idx % 2 === 0 ? "tech" : "beh",
      job_role: `Role Session ${String(id).padStart(2, "0")}`,
      difficulty: 3,
      total_questions: 5,
      answered_count: idx % 3 === 0 ? 2 : 5,
      completed: idx % 3 !== 0,
      total_score: idx % 3 !== 0 ? 70 + (idx % 25) : null,
      duration: 300 + idx * 10,
      started_at: new Date(now - daysAgo * 24 * 60 * 60 * 1000).toISOString(),
      has_resume: idx % 4 === 0,
      has_job_description: false,
    };
  });
}

function renderAuthenticatedApp(initialEntries = ["/history"]) {
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
        <MemoryRouter initialEntries={initialEntries}>
          <AppRoutes />
        </MemoryRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

describe("Dashboard Recent Sessions & Interview History", () => {
  beforeEach(() => {
    tokenStorage.clearTokens();
    vi.restoreAllMocks();
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue([]);
  });

  it("displays only the 5 newest sessions on Dashboard and navigates via View All", async () => {
    const user = userEvent.setup();
    // Deliberately pass unsorted sessions to verify newest-first sorting
    const unsorted = [
      ...makeSessions(8).slice(3),
      ...makeSessions(8).slice(0, 3),
    ];
    vi.spyOn(sessionsApi, "fetchSessions").mockResolvedValue(unsorted);

    renderAuthenticatedApp(["/dashboard"]);

    expect(
      await screen.findByRole("heading", { name: /welcome back, alex/i })
    ).toBeInTheDocument();

    // Newest 5 (Role Session 01..05) are shown in Recent Interview Sessions; 06..08 are omitted
    const recentSection = screen.getByRole("region", { name: /recent interview sessions/i });
    expect(within(recentSection).getByText("Role Session 01")).toBeInTheDocument();
    expect(within(recentSection).getByText("Role Session 05")).toBeInTheDocument();
    expect(within(recentSection).queryByText("Role Session 06")).not.toBeInTheDocument();

    const viewAllLink = screen.getByRole("link", { name: /view all/i });
    await user.click(viewAllLink);

    expect(
      await screen.findByRole("heading", { name: /interview history/i })
    ).toBeInTheDocument();
  });

  it("paginates >10 sessions across first, middle, and last pages (page size 10)", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessions").mockResolvedValueOnce(makeSessions(25));

    renderAuthenticatedApp(["/history"]);

    expect(
      await screen.findByRole("heading", { name: /interview history/i })
    ).toBeInTheDocument();

    // Page 1: items 01..10
    expect(screen.getByText("Showing 1–10 of 25 sessions")).toBeInTheDocument();
    expect(screen.getByText("Role Session 01")).toBeInTheDocument();
    expect(screen.getByText("Role Session 10")).toBeInTheDocument();
    expect(screen.queryByText("Role Session 11")).not.toBeInTheDocument();

    const prevButton = screen.getByRole("button", { name: /previous page/i });
    const nextButton = screen.getByRole("button", { name: /next page/i });
    expect(prevButton).toBeDisabled();
    expect(nextButton).toBeEnabled();

    // Middle page (Page 2): items 11..20
    await user.click(screen.getByRole("button", { name: "Page 2" }));
    expect(screen.getByText("Showing 11–20 of 25 sessions")).toBeInTheDocument();
    expect(screen.getByText("Role Session 11")).toBeInTheDocument();
    expect(screen.getByText("Role Session 20")).toBeInTheDocument();
    expect(prevButton).toBeEnabled();
    expect(nextButton).toBeEnabled();

    // Last page (Page 3): items 21..25
    await user.click(nextButton);
    expect(screen.getByText("Showing 21–25 of 25 sessions")).toBeInTheDocument();
    expect(screen.getByText("Role Session 21")).toBeInTheDocument();
    expect(screen.getByText("Role Session 25")).toBeInTheDocument();
    expect(nextButton).toBeDisabled();

    // Navigate back via Previous
    await user.click(prevButton);
    expect(screen.getByText("Showing 11–20 of 25 sessions")).toBeInTheDocument();
  });

  it("filters by search, status, and date range and resets filters", async () => {
    const user = userEvent.setup();
    const sessions = makeSessions(12);
    sessions[4].job_role = "Staff Frontend Architect";
    sessions[4].completed = true;
    vi.spyOn(sessionsApi, "fetchSessions").mockResolvedValueOnce(sessions);

    renderAuthenticatedApp(["/history"]);
    await screen.findByText("Showing 1–10 of 12 sessions");

    // Search by title
    const searchInput = screen.getByLabelText(/search by interview title or role/i);
    await user.type(searchInput, "Frontend Architect");
    expect(screen.getByText("Showing 1–1 of 1 session")).toBeInTheDocument();
    expect(screen.getByText("Staff Frontend Architect")).toBeInTheDocument();

    // Status filter mismatch -> empty filter state
    await user.selectOptions(screen.getByLabelText(/filter by status/i), "in_progress");
    expect(screen.getByText(/no matching interview sessions/i)).toBeInTheDocument();

    // Clear filters restores all 12
    await user.click(screen.getAllByRole("button", { name: /clear filters/i })[0]);
    expect(screen.getByText("Showing 1–10 of 12 sessions")).toBeInTheDocument();

    // Date filter (Last 7 days -> daysAgo 0, 3, 6 => 3 sessions)
    await user.selectOptions(screen.getByLabelText(/filter by date/i), "7d");
    expect(screen.getByText("Showing 1–3 of 3 sessions")).toBeInTheDocument();
  });

  it("renders empty history state when user has no sessions", async () => {
    vi.spyOn(sessionsApi, "fetchSessions").mockResolvedValueOnce([]);

    renderAuthenticatedApp(["/history"]);

    expect(
      await screen.findByText(/no interview sessions yet/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /start your first interview/i })
    ).toBeInTheDocument();
  });

  it("renders API error state and recovers on Retry", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessions")
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce(makeSessions(2));

    renderAuthenticatedApp(["/history"]);

    expect(
      await screen.findByText(/could not load interview history/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /retry/i }));

    expect(await screen.findByText("Showing 1–2 of 2 sessions")).toBeInTheDocument();
  });

  it("exposes Interview History in mobile navigation drawer", async () => {
    const user = userEvent.setup();
    vi.spyOn(sessionsApi, "fetchSessions").mockResolvedValue([]);

    renderAuthenticatedApp(["/dashboard"]);
    await screen.findByRole("heading", { name: /welcome back, alex/i });

    const menuButton = screen.getByRole("button", { name: /open navigation menu/i });
    await user.click(menuButton);

    const mobileNav = screen.getByRole("navigation", { name: /mobile studio navigation/i });
    const historyLink = within(mobileNav).getByRole("link", { name: /interview history/i });
    expect(historyLink).toHaveAttribute("href", "/history");

    await user.click(historyLink);
    expect(
      await screen.findByRole("heading", { name: /interview history/i })
    ).toBeInTheDocument();
  });
});

