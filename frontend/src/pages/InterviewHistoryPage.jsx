import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Filter,
  History,
  PlayCircle,
  RefreshCw,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { fetchSessions } from "../api/sessions.api.js";
import { extractApiError } from "../utils/apiErrors.js";
import { formatDuration, formatShortDate, ROLE_LABELS } from "../utils/dashboardStats.js";
import {
  DEFAULT_HISTORY_PAGE_SIZE,
  filterSessions,
  getPageNumbers,
  getSessionDisplayTitle,
  paginateSessions,
  sortSessionsNewestFirst,
} from "../utils/sessionHistory.js";
import { Badge } from "../components/ui/Badge.jsx";
import { Button } from "../components/ui/Button.jsx";

function HistorySkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-label="Loading interview history">
      <div className="rounded-2xl bg-[#0B1528] p-6 sm:p-8">
        <div className="h-7 w-56 rounded bg-white/10" />
        <div className="mt-2 h-4 w-72 max-w-full rounded bg-white/10" />
      </div>

      <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="h-10 rounded-md bg-slate-100" />
          <div className="h-10 rounded-md bg-slate-100" />
          <div className="h-10 rounded-md bg-slate-100" />
        </div>
      </div>

      <div className="space-y-3 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
        {[1, 2, 3, 4, 5].map((item) => (
          <div key={item} className="h-20 rounded-xl bg-slate-100" />
        ))}
      </div>
    </div>
  );
}

export function InterviewHistoryPage() {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);

  const loadSessions = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const data = await fetchSessions();
      setSessions(sortSessionsNewestFirst(data));
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Unable to load your interview history right now."
      );
      setErrorMessage(parsed.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const filteredSessions = useMemo(
    () =>
      filterSessions(sessions, {
        search: searchQuery,
        status: statusFilter,
        dateRange: dateFilter,
      }),
    [sessions, searchQuery, statusFilter, dateFilter]
  );

  const pagination = useMemo(
    () => paginateSessions(filteredSessions, currentPage, DEFAULT_HISTORY_PAGE_SIZE),
    [filteredSessions, currentPage]
  );

  const pageNumbers = useMemo(
    () => getPageNumbers(pagination.currentPage, pagination.totalPages),
    [pagination.currentPage, pagination.totalPages]
  );

  const hasActiveFilters =
    searchQuery.trim() !== "" || statusFilter !== "all" || dateFilter !== "all";

  function handleSearchChange(event) {
    setSearchQuery(event.target.value);
    setCurrentPage(1);
  }

  function handleStatusChange(event) {
    setStatusFilter(event.target.value);
    setCurrentPage(1);
  }

  function handleDateChange(event) {
    setDateFilter(event.target.value);
    setCurrentPage(1);
  }

  function handleClearFilters() {
    setSearchQuery("");
    setStatusFilter("all");
    setDateFilter("all");
    setCurrentPage(1);
  }

  if (isLoading) {
    return <HistorySkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Studio Header Banner */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#070D19] via-[#0B1528] to-[#0F1D3A] p-6 text-white shadow-lg sm:p-8">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-primary/25 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-20 left-1/3 h-56 w-56 rounded-full bg-secondary/20 blur-3xl"
        />

        <div className="relative flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-teal-300">
              <History className="h-3.5 w-3.5" aria-hidden="true" />
              Session Archive
            </span>
            <h1 className="font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Interview History
            </h1>
            <p className="max-w-xl text-sm text-slate-300">
              Browse all of your mock interview sessions, filter by status or date, and review past feedback.
            </p>
          </div>

          <Link to="/sessions/new" className="shrink-0">
            <Button variant="primary" size="md" className="w-full shadow-md sm:w-auto">
              <PlayCircle className="h-4 w-4" aria-hidden="true" />
              <span>Start New Interview</span>
            </Button>
          </Link>
        </div>
      </section>

      {/* Error State with Retry */}
      {errorMessage ? (
        <div
          role="alert"
          className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-destructive/30 bg-destructive-bg p-5 sm:flex-row sm:items-center"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden="true" />
            <div>
              <h2 className="text-sm font-semibold text-destructive">
                Could not load interview history
              </h2>
              <p className="mt-0.5 text-sm text-foreground-secondary">{errorMessage}</p>
            </div>
          </div>

          <Button variant="secondary" size="sm" onClick={loadSessions}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Retry</span>
          </Button>
        </div>
      ) : null}

      {/* Search & Filters Bar */}
      <section
        aria-label="Search and filter interview sessions"
        className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm sm:p-5"
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-12">
          <div className="relative md:col-span-6">
            <label htmlFor="history-search" className="sr-only">
              Search by interview title or role
            </label>
            <Search
              className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              aria-hidden="true"
            />
            <input
              id="history-search"
              type="search"
              value={searchQuery}
              onChange={handleSearchChange}
              placeholder="Search by job title or role..."
              className="block w-full rounded-lg border border-border-strong bg-surface py-2.5 pl-10 pr-3.5 text-sm text-foreground placeholder:text-foreground-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25"
            />
          </div>

          <div className="md:col-span-3">
            <label htmlFor="history-status-filter" className="sr-only">
              Filter by status
            </label>
            <div className="relative">
              <Filter
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                aria-hidden="true"
              />
              <select
                id="history-status-filter"
                value={statusFilter}
                onChange={handleStatusChange}
                className="block w-full rounded-lg border border-border-strong bg-surface py-2.5 pl-9 pr-3 text-sm text-foreground transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25"
              >
                <option value="all">All statuses</option>
                <option value="completed">Completed</option>
                <option value="in_progress">In Progress</option>
              </select>
            </div>
          </div>

          <div className="md:col-span-3">
            <label htmlFor="history-date-filter" className="sr-only">
              Filter by date
            </label>
            <select
              id="history-date-filter"
              value={dateFilter}
              onChange={handleDateChange}
              className="block w-full rounded-lg border border-border-strong bg-surface px-3.5 py-2.5 text-sm text-foreground transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25"
            >
              <option value="all">All dates</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <span>
            {pagination.totalItems === 0
              ? "Showing 0 sessions"
              : `Showing ${pagination.startItem}–${pagination.endItem} of ${pagination.totalItems} session${pagination.totalItems === 1 ? "" : "s"}`}
          </span>

          {hasActiveFilters ? (
            <button
              type="button"
              onClick={handleClearFilters}
              className="inline-flex items-center gap-1 font-semibold text-primary hover:underline"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Clear filters</span>
            </button>
          ) : null}
        </div>
      </section>

      {/* Sessions List + Pagination */}
      <section className="space-y-4 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm sm:p-6">
        {pagination.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/70 px-6 py-12 text-center">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-primary-subtle text-primary">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </div>
            <h2 className="mt-3 text-sm font-semibold text-slate-900">
              {hasActiveFilters
                ? "No matching interview sessions"
                : "No interview sessions yet"}
            </h2>
            <p className="mt-1 max-w-sm text-xs text-slate-600">
              {hasActiveFilters
                ? "Try adjusting your search or filter criteria to see more sessions."
                : "Start your first mock interview to build your practice history."}
            </p>
            {hasActiveFilters ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleClearFilters}
                className="mt-4"
              >
                Clear filters
              </Button>
            ) : (
              <Link to="/sessions/new" className="mt-4">
                <Button variant="primary" size="sm">
                  Start Your First Interview
                </Button>
              </Link>
            )}
          </div>
        ) : (
          <>
            <div className="divide-y divide-slate-200/80 rounded-xl border border-slate-200/80">
              {pagination.items.map((session) => {
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
                    className="flex flex-col justify-between gap-4 p-4 transition-colors hover:bg-slate-50/80 sm:flex-row sm:items-center"
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
                        {typeof session.total_questions === "number" ? (
                          <span>
                            {session.answered_count ?? 0} / {session.total_questions} questions
                          </span>
                        ) : null}
                        {typeof session.duration === "number" ? (
                          <span className="inline-flex items-center gap-1">
                            <Clock className="h-3 w-3" aria-hidden="true" />
                            {formatDuration(session.duration)}
                          </span>
                        ) : null}
                        <span>{formatShortDate(session.started_at)}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-4 sm:justify-end">
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

            {/* Pagination Controls */}
            {pagination.totalPages > 1 ? (
              <nav
                aria-label="Interview history pagination"
                className="flex flex-col items-center justify-between gap-3 border-t border-slate-200/80 pt-4 sm:flex-row"
              >
                <p className="text-xs text-slate-500">
                  Page {pagination.currentPage} of {pagination.totalPages}
                </p>

                <div className="flex flex-wrap items-center justify-center gap-1.5">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={!pagination.hasPrevious}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                    <span>Previous</span>
                  </Button>

                  {pageNumbers.map((pageItem) => {
                    if (typeof pageItem !== "number") {
                      return (
                        <span
                          key={pageItem}
                          aria-hidden="true"
                          className="px-2 text-xs text-slate-400"
                        >
                          …
                        </span>
                      );
                    }

                    const isCurrent = pageItem === pagination.currentPage;
                    return (
                      <button
                        key={pageItem}
                        type="button"
                        onClick={() => setCurrentPage(pageItem)}
                        aria-current={isCurrent ? "page" : undefined}
                        aria-label={`Page ${pageItem}`}
                        className={`inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-md px-2.5 text-xs font-semibold transition-colors ${
                          isCurrent
                            ? "bg-primary text-white shadow-xs"
                            : "border border-border bg-surface text-foreground-secondary hover:bg-surface-subtle hover:text-foreground"
                        }`}
                      >
                        {pageItem}
                      </button>
                    );
                  })}

                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={!pagination.hasNext}
                    onClick={() =>
                      setCurrentPage((p) => Math.min(pagination.totalPages, p + 1))
                    }
                    aria-label="Next page"
                  >
                    <span>Next</span>
                    <ChevronRight className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </nav>
            ) : null}
          </>
        )}
      </section>
    </div>
  );
}

