import { AlertCircle } from "lucide-react";
import { ConfirmDialog } from "../ui/ConfirmDialog.jsx";

export function InterviewCompletionDialog({
  isOpen,
  remainingCount = 0,
  hasUnsavedDraft = false,
  isEnding = false,
  error = "",
  onConfirm,
  onCancel,
}) {
  const baseMessage =
    remainingCount > 0
      ? `You still have ${remainingCount} unanswered question${
          remainingCount === 1 ? "" : "s"
        }. Ending now will finalize your session and generate your summary report.`
      : "Are you ready to finalize this interview session and view your summary report?";

  const description = hasUnsavedDraft
    ? `You have an unsaved response on this question that will not be submitted. ${baseMessage}`
    : baseMessage;

  return (
    <ConfirmDialog
      isOpen={isOpen}
      title="End interview session?"
      description={description}
      confirmLabel="End Interview"
      cancelLabel="Continue Practicing"
      variant="destructive"
      isLoading={isEnding}
      loadingLabel="Ending session..."
      onConfirm={onConfirm}
      onCancel={onCancel}
    >
      {error ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-destructive/25 bg-destructive-bg p-3 text-xs text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}
    </ConfirmDialog>
  );
}

