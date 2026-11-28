import {
  BookOpen,
  CheckCircle2,
  Code2,
  Compass,
  HelpCircle,
  Lightbulb,
  Sparkles,
} from "lucide-react";
import { Badge } from "../ui/Badge.jsx";
import { Card } from "../ui/Card.jsx";

function getPriorityTone(priority) {
  const norm = String(priority || "").toLowerCase();
  if (norm === "high") return "danger";
  if (norm === "medium") return "warning";
  return "teal";
}

export function RoadmapStepCard({ step }) {
  if (!step) return null;

  const objectives = Array.isArray(step.learning_objectives) ? step.learning_objectives : [];
  const questions = Array.isArray(step.interview_questions) ? step.interview_questions : [];
  const resources = Array.isArray(step.resources) ? step.resources : [];

  return (
    <Card className="p-5 sm:p-6">
      {/* Step Header */}
      <div className="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary font-mono text-sm font-bold text-primary-foreground">
            {step.order}
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-display text-lg font-bold text-foreground">
                {step.concept}
              </h3>
              <Badge tone={getPriorityTone(step.priority)}>
                {step.priority || "Medium"} Priority
              </Badge>
              {step.subject ? <Badge tone="neutral">{step.subject}</Badge> : null}
            </div>
            {step.why_needed ? (
              <p className="mt-1.5 text-sm leading-relaxed text-foreground-secondary">
                {step.why_needed}
              </p>
            ) : null}
          </div>
        </div>
      </div>

      {/* Step Body */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Left Column: Objectives + How to Learn + Example + Exercise */}
        <div className="space-y-4">
          {objectives.length > 0 ? (
            <div className="space-y-1.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-foreground-secondary">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                <span>Learning Objectives</span>
              </h4>
              <ul className="space-y-1 text-sm text-foreground">
                {objectives.map((obj, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-600" />
                    <span>{obj}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {step.how_to_learn ? (
            <div className="rounded-lg border border-border bg-surface-subtle p-3.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-foreground-secondary">
                <Compass className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                <span>How to Learn</span>
              </h4>
              <p className="mt-1.5 text-sm leading-relaxed text-foreground">
                {step.how_to_learn}
              </p>
            </div>
          ) : null}

          {step.practical_example ? (
            <div className="rounded-lg border border-border bg-surface-subtle p-3.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-foreground-secondary">
                <Code2 className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
                <span>Practical Example</span>
              </h4>
              <p className="mt-1.5 text-sm leading-relaxed text-foreground">
                {step.practical_example}
              </p>
            </div>
          ) : null}

          {step.exercise ? (
            <div className="rounded-lg border border-primary/20 bg-primary-subtle/40 p-3.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
                <Lightbulb className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Practice Exercise</span>
              </h4>
              <p className="mt-1.5 text-sm leading-relaxed text-foreground">
                {step.exercise}
              </p>
            </div>
          ) : null}
        </div>

        {/* Right Column: Interview Questions + Resources + Expected Outcome */}
        <div className="space-y-4">
          {questions.length > 0 ? (
            <div className="rounded-lg border border-border bg-surface-subtle p-3.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-foreground-secondary">
                <HelpCircle className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                <span>Interview Preparation Questions</span>
              </h4>
              <ul className="mt-2 space-y-2 text-sm text-foreground">
                {questions.map((q, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="mt-0.5 font-mono text-xs font-bold text-primary">
                      Q{idx + 1}.
                    </span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {resources.length > 0 ? (
            <div className="rounded-lg border border-border bg-surface-subtle p-3.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-foreground-secondary">
                <BookOpen className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
                <span>Recommended Resources</span>
              </h4>
              <ul className="mt-2 space-y-1.5 text-sm text-foreground">
                {resources.map((res, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary" />
                    <span>{res}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {step.expected_outcome ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50/70 p-3.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-emerald-800">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Expected Learning Outcome</span>
              </h4>
              <p className="mt-1.5 text-sm leading-relaxed text-emerald-950">
                {step.expected_outcome}
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
}

