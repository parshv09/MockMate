import { HelpCircle } from "lucide-react";
import { ROLE_LABELS } from "../../utils/dashboardStats.js";
import { SpeechTranscript } from "./SpeechTranscript.jsx";

export function QuestionDisplay({
  question,
  isAdaptive = false,
  questionKind = null,
  currentIndex = 1,
  totalQuestions = 1,
  lastEvaluation = null,
  onDismissEvaluation,
}) {
  const safeTotal = Math.max(1, Number(totalQuestions) || 1);
  const safeIndex = Math.min(Math.max(1, Number(currentIndex) || 1), safeTotal);
  const roleLabel = question?.role ? ROLE_LABELS[question.role] || question.role : "Interview";

  return (
    <div className="space-y-3">
      {!isAdaptive ? (
        <SpeechTranscript
          evaluation={lastEvaluation}
          onDismiss={onDismissEvaluation}
        />
      ) : null}

      <section
        aria-label="Current interview question"
        className="rounded-2xl border border-slate-200/90 bg-white px-5 py-4 shadow-xs sm:px-6 sm:py-5"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-primary">
              {isAdaptive
                ? `Interaction ${safeIndex} of ${safeTotal}`
                : `Question ${safeIndex} of ${safeTotal}`}
            </span>
            {isAdaptive && questionKind ? (
              <>
                <span aria-hidden="true">·</span>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                    questionKind === "follow_up"
                      ? "bg-amber-50 text-amber-700"
                      : "bg-indigo-50 text-indigo-700"
                  }`}
                >
                  {questionKind === "follow_up" ? "Follow-up" : "Main Question"}
                </span>
              </>
            ) : null}
            <span aria-hidden="true">·</span>
            <span>{roleLabel}</span>
            {typeof question?.difficulty === "number" ? (
              <>
                <span aria-hidden="true">·</span>
                <span>Level {question.difficulty}/5</span>
              </>
            ) : null}
          </div>
        </div>

        <div className="mt-2">
          {question?.text ? (
            <h1 className="font-display text-lg font-bold leading-snug text-slate-900 sm:text-xl">
              {question.text}
            </h1>
          ) : (
            <div className="flex items-center gap-2 text-slate-500">
              <HelpCircle className="h-5 w-5" aria-hidden="true" />
              <p className="text-sm font-medium">Question prompt unavailable.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

