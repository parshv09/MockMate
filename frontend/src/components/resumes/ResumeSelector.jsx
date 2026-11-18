import { FileText, RefreshCw } from "lucide-react";
import { Button } from "../ui/Button.jsx";
import { EmptyState } from "../ui/EmptyState.jsx";
import { ResumeCard } from "./ResumeCard.jsx";

/**
 * Reusable resume selection component for Resume + Job Description interview setup.
 */
export function ResumeSelector({
  resumes = [],
  selectedResumeId = null,
  onSelect,
  isLoading = false,
  error = "",
  onRetry = null,
}) {
  if (isLoading) {
    return (
      <div className="space-y-3 animate-pulse" aria-label="Loading saved resumes">
        {[1, 2].map((item) => (
          <div key={item} className="h-20 rounded-2xl bg-slate-100" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="flex flex-col items-start justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive-bg p-4 sm:flex-row sm:items-center"
      >
        <p className="text-sm text-destructive">{error}</p>
        {onRetry ? (
          <Button type="button" variant="secondary" size="sm" onClick={onRetry}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Retry</span>
          </Button>
        ) : null}
      </div>
    );
  }

  if (!resumes.length) {
    return (
      <EmptyState
        icon={FileText}
        title="No saved resumes available"
        description="Upload a resume in your Resume Vault or provide one directly during session setup."
      />
    );
  }

  return (
    <div className="space-y-3" role="radiogroup" aria-label="Select a saved resume">
      {resumes.map((resume) => (
        <ResumeCard
          key={resume.id}
          resume={resume}
          selectable
          selected={selectedResumeId === resume.id}
          onSelect={(chosen) => onSelect?.(chosen)}
        />
      ))}
    </div>
  );
}

