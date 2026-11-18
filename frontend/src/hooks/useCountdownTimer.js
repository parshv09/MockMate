/**
 * Placeholder hook for drift-free tabular countdown / elapsed timer.
 * Will be implemented in the Interview Workspace step.
 */
export function useCountdownTimer(initialSeconds = 180) {
  return {
    remainingSeconds: initialSeconds,
    isRunning: false,
  };
}
