import { Card } from "../ui/Card.jsx";
import { Badge } from "../ui/Badge.jsx";

export function ScoreOverviewBanner() {
  return (
    <Card className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div>
        <p className="text-xs font-medium text-foreground-muted">Overall Session Score</p>
        <p className="mt-1 font-mono text-2xl font-bold text-foreground tabular-nums">— / 100</p>
      </div>
      <div>
        <p className="text-xs font-medium text-foreground-muted">Video Confidence</p>
        <p className="mt-1 font-mono text-2xl font-bold text-foreground tabular-nums">— %</p>
      </div>
      <div className="flex items-center sm:justify-end">
        <Badge tone="neutral">Awaiting Session Data</Badge>
      </div>
    </Card>
  );
}

