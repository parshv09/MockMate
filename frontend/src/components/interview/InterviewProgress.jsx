import { CheckCircle2, FileText, Lightbulb, Target } from "lucide-react";
import { ROLE_LABELS } from "../../utils/dashboardStats.js";
import { getSessionDisplayTitle } from "../../utils/sessionHistory.js";

const INTERVIEW_TIPS = [
  "Lead with a concise summary before diving into details.",
  "Use real examples: Situation, Task, Action, and Result.",
  "Highlight your direct contribution and measurable outcomes.",
];

export function InterviewProgress({
  session,
  answeredCount = 0,
  totalQuestions = 0,
}) {
  const safeTotal = Math.max(0, Number(totalQuestions) || 0);
  const safeAnswered = Math.min(
    Math.max(0, Number(answeredCount) || 0),
    safeTotal || Number(answeredCount) || 0
  );
  const remainingCount = Math.max(0, safeTotal - safeAnswered);
  const completionPercent =
    safeTotal > 0 ? Math.round((safeAnswered / safeTotal) * 100) : 0;

  const title = getSessionDisplayTitle(session);
  const roleLabel = session?.role ? ROLE_LABELS[session.role] || session.role : "General";

  return (
    <div className="space-y-4">
      {/* Progress Card */}
      <section
        aria-label="Interview progress"
        className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm"
      >
        <div className="flex items-center justify-between">
          <h2 className="font-display text-sm font-bold text-slate-900">
            Session Progress
          </h2>
          <span className="font-mono text-xs font-bold text-primary tabular-nums">
            {completionPercent}%
          </span>
        </div>

        <div
          aria-hidden="true"
          className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100"
        >
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: `${completionPercent}%` }}
          />
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3">
            <dt className="text-slate-500">Completed</dt>
            <dd className="mt-1 font-mono text-lg font-bold text-slate-900 tabular-nums">
              {safeAnswered} / {safeTotal}
            </dd>
          </div>
          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3">
            <dt className="text-slate-500">Remaining</dt>
            <dd className="mt-1 font-mono text-lg font-bold text-slate-900 tabular-nums">
              {remainingCount}
            </dd>
          </div>
        </dl>

        {/* Safe Session Details */}
        <div className="mt-4 space-y-2 border-t border-slate-200/80 pt-4 text-xs text-slate-600">
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 text-slate-500">
              <Target className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
              Role
            </span>
            <span className="truncate font-semibold text-slate-800">{title}</span>
          </div>

          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 text-slate-500">
              <CheckCircle2 className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
              Category
            </span>
            <span className="font-medium text-slate-800">{roleLabel}</span>
          </div>

          {session?.resume_title ? (
            <div className="flex items-center justify-between gap-2">
              <span className="inline-flex items-center gap-1.5 text-slate-500">
                <FileText className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
                Resume
              </span>
              <span className="truncate font-medium text-slate-800">
                {session.resume_title}
              </span>
            </div>
          ) : null}
        </div>
      </section>

      {/* Coaching Tips Card */}
      <section
        aria-label="Interview tips"
        className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm"
      >
        <div className="flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-primary" aria-hidden="true" />
          <h2 className="font-display text-sm font-bold text-slate-900">
            Answering Tips
          </h2>
        </div>

        <ul className="mt-3 space-y-2 text-xs leading-relaxed text-slate-600">
          {INTERVIEW_TIPS.map((tip) => (
            <li key={tip} className="flex items-start gap-2">
              <span
                className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary"
                aria-hidden="true"
              />
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

