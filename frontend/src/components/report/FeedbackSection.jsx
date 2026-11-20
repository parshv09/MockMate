import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Lightbulb,
  Sparkles,
  TrendingUp,
  Video,
} from "lucide-react";
import { Card } from "../ui/Card.jsx";
import { Badge } from "../ui/Badge.jsx";

export function FeedbackSection({ summaryData }) {
  if (!summaryData) return null;

  const {
    strengths = [],
    improvements = [],
    overall_tip = "",
    video_summary,
    video_ai_feedback,
  } = summaryData;

  const hasStrengths = Array.isArray(strengths) && strengths.length > 0;
  const hasImprovements = Array.isArray(improvements) && improvements.length > 0;
  const videoTips = Array.isArray(video_summary?.tips) ? video_summary.tips : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-foreground">
          AI Interviewer Evaluation & Insights
        </h2>
        <Badge tone="teal">
          <Sparkles className="h-3 w-3" aria-hidden="true" />
          <span>Automated Assessment</span>
        </Badge>
      </div>

      {/* Strategic Executive Tip Callout */}
      {overall_tip ? (
        <div className="relative overflow-hidden rounded-xl border border-primary/20 bg-gradient-to-r from-primary-subtle/70 via-surface to-secondary-subtle/50 p-5 shadow-xs">
          <div className="flex items-start gap-3.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
              <Lightbulb className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-foreground">
                Executive Recommendation
              </h3>
              <p className="text-sm leading-relaxed text-foreground-secondary">
                {overall_tip}
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {/* Side-by-side Strengths and Areas for Improvement */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {/* Core Strengths */}
        <Card className="flex flex-col p-5">
          <div className="flex items-center gap-2.5 border-b border-border pb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-700">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Core Strengths</h3>
              <p className="text-xs text-foreground-muted">
                What distinguished your responses
              </p>
            </div>
          </div>

          <div className="mt-4 flex-1">
            {hasStrengths ? (
              <ul className="space-y-3">
                {strengths.map((item, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2.5 text-sm leading-relaxed text-foreground"
                  >
                    <span className="mt-2 flex h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-foreground-muted">
                Continue answering questions to build your strengths profile.
              </p>
            )}
          </div>
        </Card>

        {/* Areas for Improvement */}
        <Card className="flex flex-col p-5">
          <div className="flex items-center gap-2.5 border-b border-border pb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-amber-200 bg-amber-50 text-amber-700">
              <TrendingUp className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Areas for Growth</h3>
              <p className="text-xs text-foreground-muted">
                Actionable focus areas for higher scoring
              </p>
            </div>
          </div>

          <div className="mt-4 flex-1">
            {hasImprovements ? (
              <ul className="space-y-3">
                {improvements.map((item, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2.5 text-sm leading-relaxed text-foreground"
                  >
                    <span className="mt-2 flex h-1.5 w-1.5 shrink-0 rounded-full bg-amber-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-foreground-muted">
                No critical weaknesses detected in answered questions.
              </p>
            )}
          </div>
        </Card>
      </div>

      {/* Behavioral Intelligence Section (if video telemetry is available) */}
      {(video_ai_feedback || videoTips.length > 0) ? (
        <Card className="p-5">
          <div className="flex items-center gap-2.5 border-b border-border pb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-blue-200 bg-blue-50 text-blue-700">
              <Video className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                Behavioral & Delivery Coaching
              </h3>
              <p className="text-xs text-foreground-muted">
                Non-verbal cues, camera engagement, and poise evaluation
              </p>
            </div>
          </div>

          <div className="mt-4 space-y-4">
            {video_ai_feedback?.summary ? (
              <p className="text-xs leading-relaxed text-foreground">
                {video_ai_feedback.summary}
              </p>
            ) : null}

            {videoTips.length > 0 ? (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-foreground-secondary">
                  Camera Presence Guidance:
                </p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {videoTips.map((tip, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2 rounded-md border border-border bg-surface-subtle p-2.5 text-xs text-foreground"
                    >
                      <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
                      <span>{tip}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </Card>
      ) : null}
    </div>
  );
}

