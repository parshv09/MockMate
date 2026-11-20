import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertCircle,
  Clock,
  PlayCircle,
  RefreshCw,
} from "lucide-react";
import { fetchSessionSummary } from "../api/sessions.api.js";
import { extractApiError } from "../utils/apiErrors.js";
import { Button } from "../components/ui/Button.jsx";
import { Card } from "../components/ui/Card.jsx";
import { FeedbackSection } from "../components/report/FeedbackSection.jsx";
import { ImprovementPlan } from "../components/report/ImprovementPlan.jsx";
import { PerformanceOverview } from "../components/report/PerformanceOverview.jsx";
import { QuestionReviewList } from "../components/report/QuestionReviewList.jsx";
import { ReportHeader } from "../components/report/ReportHeader.jsx";
import { SessionSummarySkeleton } from "../components/report/SessionSummarySkeleton.jsx";

export function SessionSummaryPage() {
  const { id } = useParams();
  const [summaryData, setSummaryData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isPendingSession, setIsPendingSession] = useState(false);

  const loadSummary = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    setIsPendingSession(false);

    try {
      const data = await fetchSessionSummary(id);
      setSummaryData(data);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || "";

      // Check if session is still in progress (backend returns HTTP 400 for uncompleted sessions)
      if (
        status === 400 &&
        typeof detail === "string" &&
        detail.toLowerCase().includes("after interview completion")
      ) {
        setIsPendingSession(true);
      } else {
        const errorInfo = extractApiError(err);
        setError(errorInfo.detail || "Unable to load interview summary. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  // Loading Skeleton
  if (isLoading) {
    return <SessionSummarySkeleton />;
  }

  // Pending Session State (Session Not Completed Yet)
  if (isPendingSession) {
    return (
      <div className="mx-auto max-w-xl py-12">
        <Card className="p-8 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-amber-200 bg-amber-50 text-amber-700">
            <Clock className="h-6 w-6" aria-hidden="true" />
          </div>
          <h1 className="mt-4 font-display text-xl font-bold text-foreground">
            Interview Session in Progress
          </h1>
          <p className="mt-2 text-sm text-foreground-secondary leading-relaxed">
            Performance summaries and downloadable PDF evaluations are generated after the interview session is completed.
          </p>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link to={`/sessions/${id}/interview`}>
              <Button variant="primary" size="md">
                <PlayCircle className="h-4 w-4" aria-hidden="true" />
                <span>Return to Active Interview</span>
              </Button>
            </Link>
            <Link to="/dashboard">
              <Button variant="secondary" size="md">
                <span>Back to Dashboard</span>
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  // Error State (Network error, 404, or 500)
  if (error || !summaryData) {
    return (
      <div className="mx-auto max-w-xl py-12">
        <Card className="p-8 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-rose-200 bg-rose-50 text-rose-700">
            <AlertCircle className="h-6 w-6" aria-hidden="true" />
          </div>
          <h1 className="mt-4 font-display text-xl font-bold text-foreground">
            Could Not Load Report
          </h1>
          <p className="mt-2 text-sm text-foreground-secondary leading-relaxed">
            {error || "An unexpected error occurred while retrieving session evaluation data."}
          </p>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Button variant="primary" size="md" onClick={loadSummary}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              <span>Retry Loading</span>
            </Button>
            <Link to="/dashboard">
              <Button variant="secondary" size="md">
                <span>Back to Dashboard</span>
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  const session = summaryData.session || {};
  const answers = summaryData.answers || [];

  return (
    <div className="space-y-8 pb-12">
      {/* 1. Executive Report Header */}
      <ReportHeader session={session} summaryData={summaryData} />

      {/* 2. Quantitative Performance Overview */}
      <PerformanceOverview summaryData={summaryData} />

      {/* 3. AI Insights, Strengths, Weaknesses & Behavioral Intelligence */}
      <FeedbackSection summaryData={summaryData} />

      {/* 4. Actionable Improvement Plan & Next Steps */}
      <ImprovementPlan summaryData={summaryData} />

      {/* 5. Detailed Question-by-Question Accordion Breakdown */}
      <QuestionReviewList answers={answers} />
    </div>
  );
}
export default SessionSummaryPage;
