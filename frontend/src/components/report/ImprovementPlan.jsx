import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Compass,
  GraduationCap,
  Sparkles,
  Target,
} from "lucide-react";
import { Card } from "../ui/Card.jsx";
import { Badge } from "../ui/Badge.jsx";
import { Button } from "../ui/Button.jsx";

export function ImprovementPlan({ summaryData }) {
  if (!summaryData) return null;

  const resources = Array.isArray(summaryData.resources) ? summaryData.resources : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-foreground">
          Actionable Improvement Plan & Next Steps
        </h2>
        <Badge tone="primary">
          <Target className="h-3 w-3" aria-hidden="true" />
          <span>Growth Strategy</span>
        </Badge>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        {/* Recommended Learning Resources & Study Topics */}
        <Card className="flex flex-col p-5 lg:col-span-7">
          <div className="flex items-center gap-2 border-b border-border pb-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary-subtle text-primary">
              <BookOpen className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                Targeted Study Modules
              </h3>
              <p className="text-[11px] text-foreground-muted">
                Curated areas to deepen domain mastery
              </p>
            </div>
          </div>

          <div className="mt-4 flex-1">
            {resources.length > 0 ? (
              <ul className="space-y-2.5">
                {resources.map((res, idx) => (
                  <li
                    key={idx}
                    className="flex items-center justify-between rounded-lg border border-border bg-surface-subtle p-3 text-xs text-foreground transition-colors hover:border-border-strong hover:bg-surface"
                  >
                    <div className="flex items-center gap-2.5">
                      <GraduationCap className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                      <span className="font-medium">{res}</span>
                    </div>
                    <span className="text-[11px] font-semibold text-foreground-muted">
                      Priority Focus
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-foreground-secondary">
                Review specific question feedback above for pinpoint technical guidance.
              </p>
            )}
          </div>
        </Card>

        {/* 3-Step Interview Mastery Roadmap */}
        <Card className="flex flex-col justify-between p-5 lg:col-span-5">
          <div>
            <div className="flex items-center gap-2 border-b border-border pb-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-secondary-subtle text-secondary">
                <Compass className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Mastery Roadmap
                </h3>
                <p className="text-[11px] text-foreground-muted">
                  Suggested preparation workflow
                </p>
              </div>
            </div>

            <ol className="mt-4 space-y-3">
              <li className="flex items-start gap-2.5 text-xs text-foreground">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 font-mono text-[10px] font-bold text-primary">
                  1
                </span>
                <div>
                  <p className="font-semibold">Review Benchmark Answers</p>
                  <p className="text-[11px] text-foreground-secondary">
                    Compare your answers with model keys in the breakdown below.
                  </p>
                </div>
              </li>

              <li className="flex items-start gap-2.5 text-xs text-foreground">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 font-mono text-[10px] font-bold text-primary">
                  2
                </span>
                <div>
                  <p className="font-semibold">Refine Resume Talking Points</p>
                  <p className="text-[11px] text-foreground-secondary">
                    Address missed resume highlights and ensure evidence alignment.
                  </p>
                </div>
              </li>

              <li className="flex items-start gap-2.5 text-xs text-foreground">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 font-mono text-[10px] font-bold text-primary">
                  3
                </span>
                <div>
                  <p className="font-semibold">Repeat at Elevated Difficulty</p>
                  <p className="text-[11px] text-foreground-secondary">
                    Practice again to reinforce timed spoken articulation.
                  </p>
                </div>
              </li>
            </ol>
          </div>

          <div className="mt-6 pt-4 border-t border-border">
            <Link to="/sessions/new" className="block w-full">
              <Button variant="primary" size="md" className="w-full">
                <span>Start Next Practice Session</span>
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}

