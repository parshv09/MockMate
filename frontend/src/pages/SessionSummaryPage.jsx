import { Link, useParams } from "react-router-dom";
import { Card } from "../components/ui/Card.jsx";
import { Badge } from "../components/ui/Badge.jsx";
import { Button } from "../components/ui/Button.jsx";
import { ScoreOverviewBanner } from "../components/report/ScoreOverviewBanner.jsx";

export function SessionSummaryPage() {
  const { id } = useParams();

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <Badge tone="teal">Route: /sessions/{id}/summary</Badge>
          <h1 className="mt-2 font-display text-2xl font-bold text-foreground">
            Executive Performance Report
          </h1>
          <p className="text-sm text-foreground-secondary">
            Post-completion study view (`/api/v1/sessions/{id}/summary/`), behavioral telemetry, and PDF download (`/report/`).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/dashboard">
            <Button variant="secondary">Back to Studio</Button>
          </Link>
          <Button variant="primary" disabled>
            Download PDF Report
          </Button>
        </div>
      </div>

      <ScoreOverviewBanner />

      <Card className="space-y-2">
        <h2 className="text-base font-semibold text-foreground">
          Question-by-Question Study Accordion
        </h2>
        <p className="text-sm text-foreground-secondary">
          Submitted answers, expected reference keys, resume grounding evidence, and video behavioral coaching will render here once connected to `/api/v1/sessions/{id}/summary/`.
        </p>
      </Card>
    </div>
  );
}

