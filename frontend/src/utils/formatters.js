/**
 * Formatting helpers for timers, percentages, and question counters.
 */
export function formatDurationClock(totalSeconds = 0) {
  const safeSeconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const mins = String(Math.floor(safeSeconds / 60)).padStart(2, "0");
  const secs = String(safeSeconds % 60).padStart(2, "0");
  return `${mins}:${secs}`;
}

export function formatQuestionCounter(current = 1, total = 5) {
  return `${String(current).padStart(2, "0")} / ${String(total).padStart(2, "0")}`;
}

