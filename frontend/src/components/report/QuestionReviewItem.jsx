import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Award,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileCheck2,
  HelpCircle,
  Lightbulb,
  Mic,
  Sparkles,
  X,
} from "lucide-react";
import { Badge } from "../ui/Badge.jsx";
import { getScoreLabel, getScoreTone } from "./ScoreVisualization.jsx";

export function QuestionReviewItem({ answer, isInitiallyOpen = false }) {
  const [isOpen, setIsOpen] = useState(isInitiallyOpen);

  if (!answer) return null;

  const {
    index = 1,
    question,
    answer_text = "",
    score = null,
    feedback = "",
    improvement_tips = [],
    resume_grounding = null,
    expected_answer = "",
    has_audio = false,
  } = answer;

  const isSkipped =
    answer_text === "[Skipped]" ||
    answer_text === "" ||
    (score === 0 && feedback.toLowerCase().includes("skip"));

  const scoreTone = isSkipped ? "neutral" : getScoreTone(score);
  const questionText = question?.text || `Question #${index}`;
  const difficulty = question?.difficulty ?? 3;

  // Normalize improvement_tips (can be list of strings, JSON, or single string)
  const tipsList = Array.isArray(improvement_tips)
    ? improvement_tips
    : typeof improvement_tips === "string" && improvement_tips.trim()
    ? [improvement_tips]
    : [];

  return (
    <div
      className={`overflow-hidden rounded-xl border transition-all duration-200 ${
        isOpen
          ? "border-primary/40 bg-surface shadow-xs"
          : "border-border bg-surface hover:border-border-strong hover:bg-surface-subtle"
      }`}
    >
      {/* Accordion Header Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        className="flex w-full items-start justify-between gap-4 p-4 text-left transition-colors sm:p-5"
      >
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          {/* Top Badges */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-semibold text-primary">
              Question {index}
            </span>
            <span className="text-border-strong">•</span>
            <Badge tone="neutral">Level {difficulty}/5</Badge>

            {has_audio ? (
              <Badge tone="primary">
                <Mic className="h-3 w-3" aria-hidden="true" />
                <span>Voice Answer</span>
              </Badge>
            ) : null}

            {isSkipped ? (
              <Badge tone="warning">Skipped</Badge>
            ) : score !== null ? (
              <Badge tone={scoreTone}>
                Score: {Math.round(score)} / 100
              </Badge>
            ) : null}

            {resume_grounding ? (
              <Badge tone="teal">
                <FileCheck2 className="h-3 w-3" aria-hidden="true" />
                <span>Resume Verified</span>
              </Badge>
            ) : null}
          </div>

          {/* Question Preview Heading */}
          <p className="line-clamp-2 text-sm font-semibold text-foreground">
            {questionText}
          </p>
        </div>

        {/* Chevron Toggle Icon */}
        <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border bg-surface text-foreground-secondary transition-colors">
          {isOpen ? (
            <ChevronUp className="h-4 w-4" aria-hidden="true" />
          ) : (
            <ChevronDown className="h-4 w-4" aria-hidden="true" />
          )}
        </div>
      </button>

      {/* Accordion Collapsible Detail Body */}
      {isOpen ? (
        <div className="space-y-5 border-t border-border bg-surface-subtle/50 p-4 sm:p-6">
          {/* Full Question Prompt */}
          <div className="space-y-1.5">
            <p className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
              Full Question Prompt
            </p>
            <p className="text-sm font-medium leading-relaxed text-foreground">
              {questionText}
            </p>
          </div>

          {/* Candidate Answer Block */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                Candidate Response
              </p>
              {has_audio ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-primary">
                  <Mic className="h-3 w-3" aria-hidden="true" />
                  <span>Transcribed from Audio</span>
                </span>
              ) : null}
            </div>

            {isSkipped ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm italic text-amber-900">
                Question was skipped by candidate during the interview. No answer provided.
              </div>
            ) : (
              <div className="rounded-lg border border-border bg-surface p-4 text-sm leading-relaxed text-foreground shadow-xs">
                <p className="whitespace-pre-wrap font-sans">
                  {answer_text || "No answer recorded."}
                </p>
              </div>
            )}
          </div>

          {/* Expected Reference Benchmark Answer (Model Key) */}
          {expected_answer ? (
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
                <p className="text-xs font-semibold uppercase tracking-wider text-secondary">
                  Benchmark Reference Key
                </p>
              </div>
              <div className="rounded-lg border border-secondary/25 bg-secondary-subtle p-4 text-sm leading-relaxed text-foreground">
                <p className="whitespace-pre-wrap font-sans">{expected_answer}</p>
              </div>
            </div>
          ) : null}

          {/* Evaluator AI Feedback */}
          {feedback ? (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                AI Evaluator Feedback
              </p>
              <div className="rounded-lg border border-border bg-surface p-4 text-sm leading-relaxed text-foreground">
                <p>{feedback}</p>
              </div>
            </div>
          ) : null}

          {/* Actionable Improvement Tips */}
          {tipsList.length > 0 ? (
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Lightbulb className="h-3.5 w-3.5 text-amber-700" aria-hidden="true" />
                <p className="text-xs font-semibold uppercase tracking-wider text-amber-800">
                  Improvement Recommendations
                </p>
              </div>
              <ul className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-4">
                {tipsList.map((tip, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2.5 text-sm leading-relaxed text-foreground"
                  >
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-600" />
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* Resume Grounding Evidence Breakdown (if present) */}
          {resume_grounding && typeof resume_grounding === "object" ? (
            <div className="space-y-3 rounded-lg border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <FileCheck2 className="h-4 w-4 text-secondary" aria-hidden="true" />
                  <p className="text-xs font-semibold uppercase tracking-wider text-foreground">
                    Resume Grounding & Evidence
                  </p>
                </div>
                {resume_grounding.alignment_level ? (
                  <Badge tone="teal">
                    Alignment: {String(resume_grounding.alignment_level).toUpperCase()}
                  </Badge>
                ) : null}
              </div>

              {resume_grounding.consistency_score !== undefined ? (
                <p className="text-xs text-foreground-secondary">
                  Consistency Score:{" "}
                  <span className="font-semibold text-foreground">
                    {resume_grounding.consistency_score} / 20
                  </span>
                </p>
              ) : null}

              {/* Supported Claims */}
              {Array.isArray(resume_grounding.supported_claims) &&
              resume_grounding.supported_claims.length > 0 ? (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold text-emerald-800">
                    Verified Claims from Resume:
                  </p>
                  <ul className="space-y-1">
                    {resume_grounding.supported_claims.map((claim, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 text-sm text-foreground"
                      >
                        <Check className="mt-1 h-3.5 w-3.5 shrink-0 text-emerald-700" aria-hidden="true" />
                        <span>{claim}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {/* Missed Resume Points */}
              {Array.isArray(resume_grounding.missed_resume_points) &&
              resume_grounding.missed_resume_points.length > 0 ? (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold text-amber-800">
                    Missed Resume Highlight Opportunities:
                  </p>
                  <ul className="space-y-1">
                    {resume_grounding.missed_resume_points.map((missed, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 text-sm text-foreground"
                      >
                        <AlertTriangle className="mt-1 h-3.5 w-3.5 shrink-0 text-amber-700" aria-hidden="true" />
                        <span>{missed}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {/* Contradictions */}
              {Array.isArray(resume_grounding.contradictions) &&
              resume_grounding.contradictions.length > 0 ? (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold text-rose-800">
                    Discrepancies vs Stated Experience:
                  </p>
                  <ul className="space-y-1">
                    {resume_grounding.contradictions.map((contra, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 text-sm text-rose-900"
                      >
                        <X className="mt-1 h-3.5 w-3.5 shrink-0 text-rose-700" aria-hidden="true" />
                        <span>{contra}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

