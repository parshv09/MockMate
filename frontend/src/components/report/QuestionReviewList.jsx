import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Filter, HelpCircle, Layers } from "lucide-react";
import { Badge } from "../ui/Badge.jsx";
import { Button } from "../ui/Button.jsx";
import { QuestionReviewItem } from "./QuestionReviewItem.jsx";

export function QuestionReviewList({ answers = [] }) {
  const [filter, setFilter] = useState("all"); // 'all' | 'answered' | 'skipped'
  const [expandAllKey, setExpandAllKey] = useState(0);
  const [isAllExpanded, setIsAllExpanded] = useState(false);

  const safeAnswers = Array.isArray(answers) ? answers : [];

  const counts = useMemo(() => {
    let answered = 0;
    let skipped = 0;

    safeAnswers.forEach((a) => {
      const isSkip =
        a?.answer_text === "[Skipped]" ||
        a?.answer_text === "" ||
        (a?.score === 0 && (a?.feedback || "").toLowerCase().includes("skip"));
      if (isSkip) {
        skipped += 1;
      } else {
        answered += 1;
      }
    });

    return { total: safeAnswers.length, answered, skipped };
  }, [safeAnswers]);

  const filteredAnswers = useMemo(() => {
    if (filter === "answered") {
      return safeAnswers.filter((a) => {
        return !(
          a?.answer_text === "[Skipped]" ||
          a?.answer_text === "" ||
          (a?.score === 0 && (a?.feedback || "").toLowerCase().includes("skip"))
        );
      });
    }
    if (filter === "skipped") {
      return safeAnswers.filter((a) => {
        return (
          a?.answer_text === "[Skipped]" ||
          a?.answer_text === "" ||
          (a?.score === 0 && (a?.feedback || "").toLowerCase().includes("skip"))
        );
      });
    }
    return safeAnswers;
  }, [safeAnswers, filter]);

  const toggleExpandAll = () => {
    setIsAllExpanded((prev) => !prev);
    setExpandAllKey((prev) => prev + 1);
  };

  return (
    <div className="space-y-4">
      {/* List Header and Filter Dock */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-foreground">
              Question-by-Question Study Review
            </h2>
            <Badge tone="neutral">
              {counts.total} {counts.total === 1 ? "Question" : "Questions"}
            </Badge>
          </div>
          <p className="mt-0.5 text-xs text-foreground-secondary">
            Inspect individual candidate responses, AI scoring, and benchmark model answers.
          </p>
        </div>

        {/* Filter Pills and Expand All Toggle */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Filter Group */}
          <div className="inline-flex rounded-lg border border-border bg-surface p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setFilter("all")}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                filter === "all"
                  ? "bg-primary text-primary-foreground shadow-2xs"
                  : "text-foreground-secondary hover:text-foreground"
              }`}
            >
              All ({counts.total})
            </button>
            <button
              type="button"
              onClick={() => setFilter("answered")}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                filter === "answered"
                  ? "bg-primary text-primary-foreground shadow-2xs"
                  : "text-foreground-secondary hover:text-foreground"
              }`}
            >
              Answered ({counts.answered})
            </button>
            <button
              type="button"
              onClick={() => setFilter("skipped")}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                filter === "skipped"
                  ? "bg-primary text-primary-foreground shadow-2xs"
                  : "text-foreground-secondary hover:text-foreground"
              }`}
            >
              Skipped ({counts.skipped})
            </button>
          </div>

          {/* Expand/Collapse All Button */}
          {safeAnswers.length > 0 ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={toggleExpandAll}
              className="text-xs"
            >
              {isAllExpanded ? (
                <>
                  <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Collapse All</span>
                </>
              ) : (
                <>
                  <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Expand All</span>
                </>
              )}
            </Button>
          ) : null}
        </div>
      </div>

      {/* Accordion Questions List */}
      {filteredAnswers.length > 0 ? (
        <div key={expandAllKey} className="space-y-3">
          {filteredAnswers.map((answer, idx) => (
            <QuestionReviewItem
              key={answer.id || idx}
              answer={answer}
              isInitiallyOpen={isAllExpanded || idx === 0}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border bg-surface p-8 text-center">
          <HelpCircle className="mx-auto h-8 w-8 text-foreground-muted" aria-hidden="true" />
          <h3 className="mt-2 text-sm font-semibold text-foreground">
            No questions match this filter
          </h3>
          <p className="mt-1 text-xs text-foreground-secondary">
            Switch filters above to inspect all interview prompts.
          </p>
          <div className="mt-4">
            <Button variant="secondary" size="sm" onClick={() => setFilter("all")}>
              Show All Questions
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

