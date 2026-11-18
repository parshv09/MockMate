import { ROLE_LABELS } from "./dashboardStats.js";

export const DEFAULT_HISTORY_PAGE_SIZE = 10;

export function sortSessionsNewestFirst(sessions = []) {
  if (!Array.isArray(sessions)) return [];
  return [...sessions].sort((a, b) => {
    const timeA = a?.started_at ? new Date(a.started_at).getTime() : 0;
    const timeB = b?.started_at ? new Date(b.started_at).getTime() : 0;
    const safeA = Number.isFinite(timeA) ? timeA : 0;
    const safeB = Number.isFinite(timeB) ? timeB : 0;
    return safeB - safeA;
  });
}

export function getSessionDisplayTitle(session) {
  if (!session) return "Interview Practice";
  const roleLabel = ROLE_LABELS[session.role] || session.role || "Interview";
  return (session.job_role && session.job_role.trim()) || `${roleLabel} Practice`;
}

export function filterSessions(
  sessions = [],
  { search = "", status = "all", dateRange = "all", now = Date.now() } = {}
) {
  const normalizedSearch = search.trim().toLowerCase();
  const rangeDays =
    dateRange === "7d" ? 7 : dateRange === "30d" ? 30 : dateRange === "90d" ? 90 : null;
  const cutoffMs = rangeDays !== null ? now - rangeDays * 24 * 60 * 60 * 1000 : null;

  return sessions.filter((session) => {
    if (!session) return false;

    if (normalizedSearch) {
      const title = getSessionDisplayTitle(session).toLowerCase();
      const roleKey = String(session.role || "").toLowerCase();
      const roleLabel = String(ROLE_LABELS[session.role] || "").toLowerCase();
      const matchesSearch =
        title.includes(normalizedSearch) ||
        roleKey.includes(normalizedSearch) ||
        roleLabel.includes(normalizedSearch);
      if (!matchesSearch) return false;
    }

    if (status === "completed" && session.completed !== true) {
      return false;
    }
    if (status === "in_progress" && session.completed !== false) {
      return false;
    }

    if (cutoffMs !== null) {
      if (!session.started_at) return false;
      const startedMs = new Date(session.started_at).getTime();
      if (!Number.isFinite(startedMs) || startedMs < cutoffMs) {
        return false;
      }
    }

    return true;
  });
}

export function paginateSessions(
  sessions = [],
  page = 1,
  pageSize = DEFAULT_HISTORY_PAGE_SIZE
) {
  const safeSize = Math.max(1, Number(pageSize) || DEFAULT_HISTORY_PAGE_SIZE);
  const totalItems = sessions.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / safeSize));
  const currentPage = Math.min(Math.max(1, Number(page) || 1), totalPages);
  const startIndex = (currentPage - 1) * safeSize;
  const endIndex = Math.min(startIndex + safeSize, totalItems);

  return {
    items: sessions.slice(startIndex, endIndex),
    currentPage,
    totalPages,
    totalItems,
    pageSize: safeSize,
    startItem: totalItems === 0 ? 0 : startIndex + 1,
    endItem: endIndex,
    hasPrevious: currentPage > 1,
    hasNext: currentPage < totalPages,
  };
}

export function getPageNumbers(currentPage, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, idx) => idx + 1);
  }

  const pages = [1];
  const left = Math.max(2, currentPage - 1);
  const right = Math.min(totalPages - 1, currentPage + 1);

  if (left > 2) {
    pages.push("ellipsis-left");
  }

  for (let p = left; p <= right; p += 1) {
    pages.push(p);
  }

  if (right < totalPages - 1) {
    pages.push("ellipsis-right");
  }

  pages.push(totalPages);
  return pages;
}

