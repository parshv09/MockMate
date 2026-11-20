import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  Download,
  FileCheck2,
  Loader2,
  RotateCcw,
} from "lucide-react";
import { Badge } from "../ui/Badge.jsx";
import { Button } from "../ui/Button.jsx";
import { ROLE_LABELS } from "../../utils/dashboardStats.js";
import { getSessionDisplayTitle } from "../../utils/sessionHistory.js";
import { triggerReportDownload } from "../../api/sessions.api.js";
import { useToast } from "../../context/ToastContext.jsx";

export function ReportHeader({ session, summaryData }) {
  const [isDownloading, setIsDownloading] = useState(false);
  const toast = useToast();

  const title = getSessionDisplayTitle(session);
  const roleLabel = ROLE_LABELS[session?.role] || session?.role || "Interview";
  const difficulty = session?.difficulty ?? 3;
  const isCompleted = Boolean(session?.completed || session?.is_completed);

  const formattedDate = session?.completed_at
    ? new Date(session.completed_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : session?.started_at
    ? new Date(session.started_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Completed";

  const durationMin = summaryData?.duration_minutes ?? session?.duration ?? 0;

  const handleDownload = async () => {
    if (!session?.id || isDownloading) return;
    try {
      setIsDownloading(true);
      await triggerReportDownload(session.id);
      toast?.showToast?.({
        title: "Report Downloaded",
        description: `Executive PDF for session #${session.id} saved.`,
        tone: "success",
      });
    } catch (err) {
      toast?.showToast?.({
        title: "Download Failed",
        description:
          err?.response?.data?.detail || "Could not generate PDF report. Please try again.",
        tone: "error",
      });
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-6 shadow-xs">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        {/* Title, Meta Badges, and Details */}
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-foreground-secondary transition-colors hover:text-foreground"
            >
              <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Back to Dashboard</span>
            </Link>
            <span className="text-border-strong">•</span>
            <Badge tone={isCompleted ? "success" : "warning"}>
              <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
              <span>{isCompleted ? "Session Completed" : "In Progress"}</span>
            </Badge>
            <Badge tone="primary">{roleLabel}</Badge>
            <Badge tone="neutral">Difficulty: Level {difficulty}/5</Badge>
            {session?.has_resume ? (
              <Badge tone="teal">
                <FileCheck2 className="h-3 w-3" aria-hidden="true" />
                <span>Resume Grounded</span>
              </Badge>
            ) : null}
          </div>

          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              {title}
            </h1>
            <p className="mt-1 flex flex-wrap items-center gap-3 text-xs text-foreground-secondary">
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{formattedDate}</span>
              </span>
              <span>•</span>
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{durationMin} {durationMin === 1 ? "minute" : "minutes"} duration</span>
              </span>
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3 sm:self-start lg:self-center">
          <Link to="/sessions/new">
            <Button variant="secondary" size="md">
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              <span>Practice Again</span>
            </Button>
          </Link>

          <Button
            variant="primary"
            size="md"
            onClick={handleDownload}
            disabled={!isCompleted || isDownloading}
            isLoading={isDownloading}
          >
            {isDownloading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                <span>Generating PDF...</span>
              </>
            ) : (
              <>
                <Download className="h-4 w-4" aria-hidden="true" />
                <span>Download PDF Report</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

