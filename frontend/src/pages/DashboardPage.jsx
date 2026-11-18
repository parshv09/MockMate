import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock,
  FileText,
  Layers,
  PlayCircle,
  RefreshCw,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { fetchSessions } from "../api/sessions.api.js";
import { fetchResumes } from "../api/resumes.api.js";
import { extractApiError } from "../utils/apiErrors.js";
import {
  computeDashboardStats,
  formatDuration,
  formatShortDate,
  ROLE_LABELS,
} from "../utils/dashboardStats.js";
import {
  getSessionDisplayTitle,
  sortSessionsNewestFirst,
} from "../utils/sessionHistory.js";
import { Badge } from "../components/ui/Badge.jsx";
import { Button } from "../components/ui/Button.jsx";

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-label="Loading dashboard">
      <div className="rounded-2xl bg-[#0B1528] p-6 sm:p-8">
        <div className="h-7 w-56 rounded bg-white/10" />
        <div className="mt-2 h-4 w-80 max-w-full rounded bg-white/10" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((item) => (
          <div key={item} className="space-y-3 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm">
            <div className="h-3.5 w-24 rounded bg-slate-200" />
            <div className="h-8 w-16 rounded bg-slate-200" />
            <div className="h-3 w-32 rounded bg-slate-200" />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-4 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm lg:col-span-2">
          <div className="h-5 w-44 rounded bg-slate-200" />
          <div className="space-y-3">
            {[1, 2, 3].map((row) => (
              <div key={row} className="h-16 rounded-xl bg-slate-100" />
            ))}
          </div>
        </div>
        <div className="space-y-4 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
          <div className="h-5 w-36 rounded bg-slate-200" />
          <div className="space-y-3">
            {[1, 2].map((row) => (
              <div key={row} className="h-14 rounded-xl bg-slate-100" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [resumes, setResumes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const loadDashboardData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const [sessionList, resumeList] = await Promise.all([
        fetchSessions(),
        fetchResumes(),
      ]);
      setSessions(sessionList);
      setResumes(resumeList);
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Unable to load your dashboard data right now."
      );
      setErrorMessage(parsed.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const stats = useMemo(
    () => computeDashboardStats(sessions, resumes),
    [sessions, resumes]
  );

  const recentSessions = useMemo(
    () => sortSessionsNewestFirst(sessions).slice(0, 5),
    [sessions]
  );
  const recentResumes = useMemo(() => resumes.slice(0, 4), [resumes]);

  const firstName = user?.first_name?.trim() || user?.username || "there";

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Studio Welcome Banner (matching Landing Hero navy gradient + glows) */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#070D19] via-[#0B1528] to-[#0F1D3A] p-6 text-white shadow-lg sm:p-8">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-primary/25 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-20 left-1/3 h-56 w-56 rounded-full bg-secondary/20 blur-3xl"
        />

        <div className="relative flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-teal-300">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              Practice Studio
            </span>
            <h1 className="font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Welcome back, {firstName}
            </h1>
            <p className="max-w-xl text-sm leading-relaxed text-slate-300">
              {user?.target_role
                ? `Preparing for ${user.target_role} interviews. Start a new practice round or review your recent feedback.`
                : "Track your practice sessions, review your scores, and keep your resumes ready for tailored interviews."}
            </p>
          </div>

          <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center">
            <Link to="/sessions/new" className="shrink-0">
              <Button variant="primary" size="md" className="w-full shadow-md sm:w-auto">
                <PlayCircle className="h-4 w-4" aria-hidden="true" />
                <span>Start New Interview</span>
              </Button>
            </Link>
            <Link
              to="/resumes"
              className="inline-flex min-h-[40px] items-center justify-center rounded-md border border-white/20 bg-white/5 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/10"
            >
              Resume Vault
            </Link>
          </div>
        </div>
      </section>

      {/* Error & Retry Banner */}
      {errorMessage ? (
        <div
          role="alert"
          className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-destructive/30 bg-destructive-bg p-5 sm:flex-row sm:items-center"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden="true" />
            <div>
              <h2 className="text-sm font-semibold text-destructive">
                Could not load studio data
              </h2>
              <p className="mt-0.5 text-sm text-foreground-secondary">{errorMessage}</p>
            </div>
          </div>

          <Button variant="secondary" size="sm" onClick={loadDashboardData}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Retry</span>
          </Button>
        </div>
      ) : null}

      {/* Statistics Grid (derived strictly from real API data) */}
      <section aria-label="Interview statistics" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Total Sessions
            </span>
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-subtle text-primary">
              <Layers className="h-4 w-4" aria-hidden="true" />
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-slate-900 tabular-nums">
            {stats.totalSessions}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {stats.totalSessions === 0
              ? "No practice sessions yet"
              : `${stats.completedCount} completed · ${stats.inProgressCount} in progress`}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Average Score
            </span>
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary-subtle text-secondary">
              <TrendingUp className="h-4 w-4" aria-hidden="true" />
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-slate-900 tabular-nums">
            {stats.averageScore !== null ? `${stats.averageScore}%` : "—"}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {stats.scoredCount > 0
              ? `Across ${stats.scoredCount} scored session${stats.scoredCount === 1 ? "" : "s"}`
              : "Complete a session to see your average"}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Questions Answered
            </span>
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-success-bg text-success">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-slate-900 tabular-nums">
            {stats.totalQuestionsAnswered}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {stats.totalQuestionsAnswered === 0
              ? "Start practicing to track responses"
              : "Total responses evaluated"}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Saved Resumes
            </span>
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary-subtle text-secondary">
              <FileText className="h-4 w-4" aria-hidden="true" />
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-slate-900 tabular-nums">
            {stats.totalResumes}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {stats.totalResumes > 0
              ? "Available for tailored interviews"
              : "Upload a resume for tailored questions"}
          </p>
        </div>
      </section>

      {/* Score Trend Visualization (only shown when >= 2 real scored sessions exist) */}
      {stats.scoreTrend.length >= 2 ? (
        <div className="space-y-4 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="font-display text-base font-bold text-slate-900">
                Recent Score Progression
              </h2>
            </div>
            <span className="text-xs text-slate-500">
              Last {stats.scoreTrend.length} scored sessions
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
            {stats.scoreTrend.map((point) => (
              <div
                key={point.id}
                className="flex flex-col justify-end rounded-xl border border-slate-200/80 bg-slate-50 p-3"
              >
                <div className="mb-2 flex h-20 items-end">
                  <div
                    className="w-full rounded-md bg-gradient-to-t from-primary to-secondary transition-all duration-300"
                    style={{ height: `${Math.max(12, Math.min(100, point.score))}%` }}
                    aria-label={`${point.label}: ${point.score}%`}
                  />
                </div>
                <p className="font-mono text-sm font-bold text-slate-900 tabular-nums">
                  {point.score}%
                </p>
                <p className="truncate text-xs text-slate-600" title={point.label}>
                  {point.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Main Content Split: Recent Sessions & Resume Overview */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Recent Interview Sessions */}
        <section
          aria-label="Recent interview sessions"
          className="space-y-4 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm lg:col-span-2"
        >
          <div className="flex items-center justify-between gap-2">
            <div>
              <h2 className="font-display text-base font-bold text-slate-900">
                Recent Interview Sessions
              </h2>
              <p className="text-xs text-slate-500">
                Your 5 most recent mock interviews
              </p>
            </div>
            <Link
              to="/history"
              className="inline-flex items-center gap-1 rounded-md border border-primary/20 bg-primary-subtle px-3 py-1.5 text-xs font-semibold text-primary transition-colors hover:bg-primary hover:text-white"
            >
              <span>View All</span>
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </div>

          {recentSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/70 px-6 py-10 text-center">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-primary-subtle text-primary">
                <Sparkles className="h-5 w-5" aria-hidden="true" />
              </div>
              <h3 className="mt-3 text-sm font-semibold text-slate-900">
                No interview sessions yet
              </h3>
              <p className="mt-1 max-w-sm text-xs text-slate-600">
                Start a standard role practice or upload your resume to practice tailored questions.
              </p>
              <Link to="/sessions/new" className="mt-4">
                <Button variant="primary" size="sm">
                  Start Your First Interview
                </Button>
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-slate-200/80 rounded-xl border border-slate-200/80">
              {recentSessions.map((session) => {
                const roleLabel = ROLE_LABELS[session.role] || session.role || null;
                const title = getSessionDisplayTitle(session);
                const isTailored = Boolean(session.has_resume || session.has_job_description);
                const hasStatus = typeof session.completed === "boolean";
                const hasScore =
                  session.completed === true &&
                  typeof session.total_score === "number" &&
                  Number.isFinite(session.total_score);

                return (
                  <div
                    key={session.id}
                    className="flex flex-col justify-between gap-3 p-4 transition-colors hover:bg-slate-50/80 sm:flex-row sm:items-center"
                  >
                    <div className="min-w-0 space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="truncate text-sm font-semibold text-slate-900">
                          {title}
                        </span>
                        {roleLabel ? <Badge tone="neutral">{roleLabel}</Badge> : null}
                        {isTailored ? <Badge tone="teal">Resume + JD</Badge> : null}
                        {hasStatus ? (
                          <Badge tone={session.completed ? "success" : "warning"}>
                            {session.completed ? "Completed" : "In Progress"}
                          </Badge>
                        ) : null}
                      </div>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                        <span>
                          {session.answered_count ?? 0} / {session.total_questions ?? 0} questions
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <Clock className="h-3 w-3" aria-hidden="true" />
                          {formatDuration(session.duration)}
                        </span>
                        <span>{formatShortDate(session.started_at)}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-3 sm:justify-end">
                      <div className="text-left sm:text-right">
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">
                          Score
                        </p>
                        <p className="font-mono text-sm font-bold text-slate-900 tabular-nums">
                          {hasScore ? `${Math.round(session.total_score)}%` : "—"}
                        </p>
                      </div>

                      <Link
                        to={
                          session.completed
                            ? `/sessions/${session.id}/summary`
                            : `/sessions/${session.id}/interview`
                        }
                      >
                        <Button variant="secondary" size="sm">
                          {session.completed ? "View Report" : "Continue"}
                        </Button>
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Resume Overview */}
        <div className="flex flex-col justify-between space-y-4 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <h2 className="font-display text-base font-bold text-slate-900">
                  Resume Overview
                </h2>
                <p className="text-xs text-slate-500">
                  Documents ready for tailored interviews
                </p>
              </div>
              <Link
                to="/resumes"
                className="text-xs font-semibold text-primary hover:underline"
              >
                Manage
              </Link>
            </div>

            {recentResumes.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/70 px-4 py-8 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary-subtle text-secondary">
                  <FileText className="h-5 w-5" aria-hidden="true" />
                </div>
                <h3 className="mt-3 text-sm font-semibold text-slate-900">
                  No resumes uploaded
                </h3>
                <p className="mt-1 text-xs text-slate-600">
                  Add your resume in the Resume Vault to unlock personalized interview questions.
                </p>
                <Link to="/resumes" className="mt-4">
                  <Button variant="secondary" size="sm">
                    Go to Resume Vault
                  </Button>
                </Link>
              </div>
            ) : (
              <ul className="space-y-2.5">
                {recentResumes.map((resume) => (
                  <li
                    key={resume.id}
                    className="flex items-start justify-between gap-3 rounded-xl border border-slate-200/80 bg-slate-50/60 p-3.5"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">
                        {resume.title || "Untitled Resume"}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-slate-500">
                        {resume.file_name || "Saved resume text"} ·{" "}
                        {formatShortDate(resume.updated_at || resume.created_at)}
                      </p>
                    </div>
                    <Badge tone="teal">Ready</Badge>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {recentResumes.length > 0 ? (
            <Link to="/resumes" className="block pt-2">
              <Button variant="secondary" size="sm" className="w-full">
                Open Resume Vault
              </Button>
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
}
