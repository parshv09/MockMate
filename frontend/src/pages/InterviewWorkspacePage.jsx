import { Link, useParams } from "react-router-dom";
import { Card } from "../components/ui/Card.jsx";
import { Badge } from "../components/ui/Badge.jsx";
import { Button } from "../components/ui/Button.jsx";
import { WebcamTelemetryRail } from "../components/interview/WebcamTelemetryRail.jsx";

export function InterviewWorkspacePage() {
  const { id } = useParams();

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <div className="space-y-6 lg:col-span-8">
        <Card className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Badge tone="primary">Session #{id}</Badge>
              <Badge tone="teal">Resume-Grounded Prompt</Badge>
            </div>
            <span className="font-mono text-sm font-semibold text-foreground tabular-nums">
              02:30
            </span>
          </div>

          <h1 className="font-display text-xl font-semibold leading-snug text-foreground max-w-[70ch]">
            Interview question prompt stage (`/api/v1/sessions/{id}/next-question/`) — live prompt loading will be wired in the Interview Workspace step.
          </h1>
        </Card>

        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">
              Answer Composer (Voice &amp; Written Text)
            </h2>
            <span className="text-xs text-foreground-muted">
              Sequential lock enforced
            </span>
          </div>

          <div className="rounded-md border border-border bg-surface-subtle p-4 text-xs text-foreground-muted">
            Whisper audio upload and text submission (`/api/v1/sessions/{id}/answers/` and `/skip/`) will be connected in the Interview Workspace step.
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <Button variant="secondary" disabled>
              Skip Question
            </Button>
            <Link to={`/sessions/${id}/summary`}>
              <Button variant="primary">Preview Summary Report</Button>
            </Link>
          </div>
        </Card>
      </div>

      <div className="lg:col-span-4">
        <WebcamTelemetryRail />
      </div>
    </div>
  );
}

