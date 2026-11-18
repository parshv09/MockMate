/**
 * Derives dashboard metrics strictly from real /api/v1/sessions/ and /api/v1/resumes/
 * responses. Never fabricates scores, counts, or session history.
 */

export const ROLE_LABELS = {
  tech: "Technical",
  hr: "HR",
  apt: "Aptitude",
  beh: "Behavioral",
};

export function computeDashboardStats(sessions = [], resumes = []) {
  const safeSessions = Array.isArray(sessions) ? sessions : [];
  const safeResumes = Array.isArray(resumes) ? resumes : [];

  const totalSessions = safeSessions.length;
  const completedSessions = safeSessions.filter((s) => Boolean(s?.completed));
  const inProgressSessions = totalSessions - completedSessions.length;

  const scoredSessions = completedSessions.filter(
    (s) => typeof s?.total_score === "number" && Number.isFinite(s.total_score)
  );

  const averageScore =
    scoredSessions.length > 0
      ? Math.round(
          (scoredSessions.reduce((sum, s) => sum + s.total_score, 0) /
            scoredSessions.length) *
            10
        ) / 10
      : null;

  const totalQuestionsAnswered = safeSessions.reduce(
    (sum, s) => sum + (Number.isFinite(s?.answered_count) ? s.answered_count : 0),
    0
  );

  // Sort chronological ascending for score trend visualization
  const scoreTrend = [...scoredSessions]
    .sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime())
    .slice(-6)
    .map((s) => ({
      id: s.id,
      label: s.job_role || ROLE_LABELS[s.role] || "Interview",
      score: Math.round(s.total_score),
      startedAt: s.started_at,
    }));

  return {
    totalSessions,
    completedCount: completedSessions.length,
    inProgressCount: inProgressSessions,
    scoredCount: scoredSessions.length,
    averageScore,
    totalQuestionsAnswered,
    totalResumes: safeResumes.length,
    scoreTrend,
  };
}

export function formatShortDate(isoString) {
  if (!isoString) return "—";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatDuration(seconds) {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) {
    return "—";
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

