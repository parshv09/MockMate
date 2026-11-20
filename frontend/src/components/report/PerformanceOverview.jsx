import {
  Award,
  BarChart3,
  CheckCircle,
  Clock,
  Eye,
  FileCheck,
  Percent,
  Sparkles,
  TrendingUp,
  Video,
} from "lucide-react";
import { Card } from "../ui/Card.jsx";
import { Badge } from "../ui/Badge.jsx";
import { ScoreGauge, getScoreTone, getScoreLabel } from "./ScoreVisualization.jsx";

export function PerformanceOverview({ summaryData }) {
  if (!summaryData) return null;

  const {
    session,
    average_score,
    content_quality_score,
    completion_rate = 0,
    duration_minutes = 0,
    resume_summary,
    video_summary,
  } = summaryData;

  const answersList = Array.isArray(summaryData.answers) ? summaryData.answers : [];
  const totalQuestions = answersList.length || session?.total_questions || 0;
  const attemptedCount =
    answersList.length > 0
      ? answersList.filter(
          (a) =>
            a?.answer_text &&
            !["[Skipped]", "", "[Voice answer could not be transcribed]"].includes(
              a.answer_text.trim()
            )
        ).length
      : session?.answered_count ?? 0;
  const voiceCount = answersList.filter((a) => a?.has_audio).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-foreground">
          Performance Overview
        </h2>
        <Badge tone="neutral">
          <BarChart3 className="h-3 w-3" aria-hidden="true" />
          <span>Aggregated Telemetry</span>
        </Badge>
      </div>

      {/* Main Score Hero Card */}
      <Card className="grid grid-cols-1 items-center gap-6 p-6 md:grid-cols-12">
        {/* Left Column: Primary Circular Score Gauge */}
        <div className="flex flex-col items-center justify-center border-b border-border pb-6 md:col-span-5 md:border-b-0 md:border-r md:pb-0 md:pr-6">
          <ScoreGauge
            score={average_score}
            size={160}
            strokeWidth={12}
            label="Overall Session Score"
          />
          <p className="mt-3 max-w-xs text-center text-xs text-foreground-secondary">
            Weighted composite based on question difficulty, technical depth, and communication clarity.
          </p>
        </div>

        {/* Right Column: Secondary Key Metrics Breakdown */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:col-span-7">
          {/* Content Quality */}
          <div className="rounded-lg border border-border bg-surface-subtle p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground-secondary">
                Answer Quality Score
              </span>
              <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-mono text-2xl font-bold text-foreground">
                {content_quality_score !== null && content_quality_score !== undefined
                  ? Math.round(content_quality_score)
                  : "—"}
              </span>
              <span className="text-xs font-semibold text-foreground-muted">/ 100</span>
            </div>
            <p className="mt-1 text-[11px] text-foreground-muted">
              Evaluated strictly across answered questions (excluding skips).
            </p>
          </div>

          {/* Completion Rate */}
          <div className="rounded-lg border border-border bg-surface-subtle p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground-secondary">
                Completion Rate
              </span>
              <CheckCircle className="h-4 w-4 text-emerald-600" aria-hidden="true" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-mono text-2xl font-bold text-foreground">
                {completion_rate}%
              </span>
              <span className="text-xs font-medium text-foreground-secondary">
                ({attemptedCount} of {totalQuestions} attempted)
              </span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full bg-emerald-600 transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, completion_rate))}%` }}
              />
            </div>
          </div>

          {/* Interview Duration */}
          <div className="rounded-lg border border-border bg-surface-subtle p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground-secondary">
                Session Duration
              </span>
              <Clock className="h-4 w-4 text-foreground-muted" aria-hidden="true" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-mono text-2xl font-bold text-foreground">
                {duration_minutes}
              </span>
              <span className="text-xs font-medium text-foreground-secondary">
                {duration_minutes === 1 ? "minute" : "minutes"}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-foreground-muted">
              Total active interview time from first prompt to completion.
            </p>
          </div>

          {/* Questions Processed */}
          <div className="rounded-lg border border-border bg-surface-subtle p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground-secondary">
                Questions Processed
              </span>
              <TrendingUp className="h-4 w-4 text-secondary" aria-hidden="true" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-mono text-2xl font-bold text-foreground">
                {totalQuestions}
              </span>
              <span className="text-xs font-medium text-foreground-secondary">
                {totalQuestions === 1 ? "prompt" : "prompts"}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-foreground-muted">
              {voiceCount > 0
                ? `${voiceCount} voice ${voiceCount === 1 ? "response" : "responses"} recorded`
                : "Standard text evaluation"}
            </p>
          </div>
        </div>
      </Card>

      {/* Auxiliary Behavioral & Resume Intelligence Cards (if available) */}
      {(resume_summary || video_summary) ? (
        <div
          className={`grid grid-cols-1 gap-4 ${
            resume_summary && video_summary ? "md:grid-cols-2" : ""
          }`}
        >
          {/* Resume Grounding Card */}
          {resume_summary ? (
            <Card className="p-4 sm:p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileCheck className="h-4 w-4 text-secondary" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-foreground">
                    Resume Alignment & Verification
                  </h3>
                </div>
                <Badge tone="teal">{resume_summary.consistency_pct}% Match</Badge>
              </div>

              <p className="mt-1 text-xs text-foreground-secondary">
                Grounding analysis against saved profile:{" "}
                <span className="font-medium text-foreground">{resume_summary.resume_title}</span>
              </p>

              <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                  <p className="text-xs font-semibold text-emerald-800">
                    Verified
                  </p>
                  <p className="mt-1 font-mono text-lg font-bold text-emerald-900">
                    {resume_summary.supported_count}
                  </p>
                </div>
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                  <p className="text-xs font-semibold text-amber-800">
                    Missed Points
                  </p>
                  <p className="mt-1 font-mono text-lg font-bold text-amber-900">
                    {resume_summary.missed_count}
                  </p>
                </div>
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
                  <p className="text-xs font-semibold text-rose-800">
                    Discrepancies
                  </p>
                  <p className="mt-1 font-mono text-lg font-bold text-rose-900">
                    {resume_summary.contradictions_count}
                  </p>
                </div>
              </div>
            </Card>
          ) : null}

          {/* Behavioral Video Confidence Card */}
          {video_summary ? (
            <Card className="p-4 sm:p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Video className="h-4 w-4 text-primary" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-foreground">
                    Behavioral Video Telemetry
                  </h3>
                </div>
                <Badge tone="primary">
                  {video_summary.confidence_score}% Confidence
                </Badge>
              </div>

              <p className="mt-1 text-xs text-foreground-secondary">
                Engagement assessment:{" "}
                <span className="font-semibold text-foreground">
                  {video_summary.engagement_level || "Analyzed"}
                </span>
              </p>

              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-md border border-border bg-surface-subtle p-2">
                  <p className="text-[11px] font-medium text-foreground-secondary">
                    Presence
                  </p>
                  <p className="mt-0.5 font-mono text-base font-bold text-foreground">
                    {video_summary.presence_pct}%
                  </p>
                </div>
                <div className="rounded-md border border-border bg-surface-subtle p-2">
                  <p className="text-[11px] font-medium text-foreground-secondary">
                    Eye Contact
                  </p>
                  <p className="mt-0.5 font-mono text-base font-bold text-foreground">
                    {video_summary.eye_contact_pct}%
                  </p>
                </div>
                <div className="rounded-md border border-border bg-surface-subtle p-2">
                  <p className="text-[11px] font-medium text-foreground-secondary">
                    Stability
                  </p>
                  <p className="mt-0.5 font-mono text-base font-bold text-foreground">
                    {Math.round(100 - (video_summary.movement_pct || 0))}%
                  </p>
                </div>
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

