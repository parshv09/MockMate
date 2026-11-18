import { Calendar, CheckCircle2, FileText, Trash2 } from "lucide-react";
import { formatShortDate } from "../../utils/dashboardStats.js";
import { getFileExtension } from "../../utils/resumeValidation.js";
import { Badge } from "../ui/Badge.jsx";
import { Button } from "../ui/Button.jsx";

function getFormatBadgeLabel(resume) {
  if (!resume?.has_file) {
    return "Text";
  }
  const ext = getFileExtension(resume.file_name || "");
  if (ext) {
    return ext.slice(1).toUpperCase();
  }
  return "File";
}

export function ResumeCard({
  resume,
  onDelete = null,
  isDeleting = false,
  selectable = false,
  selected = false,
  onSelect = null,
}) {
  if (!resume) return null;

  const title = resume.title?.trim() || "Untitled Resume";
  const formatLabel = getFormatBadgeLabel(resume);
  const displayDate = formatShortDate(resume.updated_at || resume.created_at);

  const cardContent = (
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div className="flex min-w-0 items-start gap-3.5">
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${
            selected
              ? "bg-primary text-white"
              : "bg-secondary-subtle text-secondary"
          }`}
        >
          {selected ? (
            <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
          ) : (
            <FileText className="h-5 w-5" aria-hidden="true" />
          )}
        </div>

        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-slate-900">
              {title}
            </h3>
            <Badge tone={resume.has_file ? "teal" : "neutral"}>{formatLabel}</Badge>
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
            <span className="truncate">
              {resume.file_name || "Saved resume text"}
            </span>
            <span className="inline-flex items-center gap-1">
              <Calendar className="h-3 w-3" aria-hidden="true" />
              <span>Added {displayDate}</span>
            </span>
          </div>
        </div>
      </div>

      {onDelete && !selectable ? (
        <div className="flex items-center justify-end gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={isDeleting}
            onClick={() => onDelete(resume)}
            aria-label={`Delete ${title}`}
            className="text-destructive hover:bg-destructive-bg hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            <span>Delete</span>
          </Button>
        </div>
      ) : null}
    </div>
  );

  if (selectable) {
    return (
      <button
        type="button"
        onClick={() => onSelect?.(resume)}
        aria-pressed={selected}
        className={`w-full rounded-2xl border p-4 text-left transition-all ${
          selected
            ? "border-primary bg-primary-subtle/50 ring-2 ring-primary/20"
            : "border-slate-200/80 bg-white hover:border-slate-300 hover:shadow-xs"
        }`}
      >
        {cardContent}
      </button>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm transition-shadow hover:shadow-md sm:p-5">
      {cardContent}
    </div>
  );
}
