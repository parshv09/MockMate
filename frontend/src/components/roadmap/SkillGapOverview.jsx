import { AlertTriangle, Layers, Target } from "lucide-react";
import { Badge } from "../ui/Badge.jsx";
import { Card } from "../ui/Card.jsx";

function getPriorityTone(priority) {
  const norm = String(priority || "").toLowerCase();
  if (norm === "high") return "danger";
  if (norm === "medium") return "warning";
  return "teal";
}

export function SkillGapOverview({ skillGaps = [] }) {
  const gaps = Array.isArray(skillGaps) ? skillGaps : [];

  return (
    <section aria-label="Skill-gap analysis" className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" aria-hidden="true" />
          <h2 className="text-base font-semibold text-foreground">
            Identified Skill Gaps &amp; Priorities
          </h2>
        </div>
        <Badge tone="neutral">
          {gaps.length} {gaps.length === 1 ? "Concept" : "Concepts"}
        </Badge>
      </div>

      {gaps.length === 0 ? (
        <Card className="p-5 text-sm text-foreground-secondary">
          No critical skill gaps were flagged from this session. Follow the enrichment steps below to deepen your mastery.
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {gaps.map((gap, idx) => {
            const weaknesses = Array.isArray(gap.demonstrated_weaknesses)
              ? gap.demonstrated_weaknesses
              : [];
            const opportunities = Array.isArray(gap.improvement_opportunities)
              ? gap.improvement_opportunities
              : [];
            const notes = weaknesses.length > 0 ? weaknesses : opportunities;

            return (
              <Card key={`${gap.concept || idx}-${idx}`} className="flex flex-col justify-between p-4">
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-display text-sm font-bold text-foreground">
                        {gap.concept}
                      </h3>
                      <p className="mt-0.5 flex items-center gap-1 text-[11px] text-foreground-muted">
                        <Layers className="h-3 w-3" aria-hidden="true" />
                        <span>{gap.subject || "General"}</span>
                      </p>
                    </div>
                    <Badge tone={getPriorityTone(gap.priority)}>
                      {gap.priority || "Medium"} Priority
                    </Badge>
                  </div>

                  {notes.length > 0 ? (
                    <ul className="space-y-1 text-xs text-foreground-secondary">
                      {notes.slice(0, 2).map((note, nIdx) => (
                        <li key={nIdx} className="flex items-start gap-1.5">
                          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-600" aria-hidden="true" />
                          <span>{note}</span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>

                {typeof gap.avg_score === "number" ? (
                  <div className="mt-3 border-t border-border pt-2.5 text-[11px] text-foreground-muted">
                    Average Score: <span className="font-mono font-semibold text-foreground">{Math.round(gap.avg_score)}%</span>
                  </div>
                ) : null}
              </Card>
            );
          })}
        </div>
      )}
    </section>
  );
}

