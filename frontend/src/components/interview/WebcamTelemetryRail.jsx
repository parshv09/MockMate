import { Video, Eye, CheckCircle2 } from "lucide-react";

export function WebcamTelemetryRail() {
  return (
    <section
      aria-label="Live Camera and Behavioral Telemetry Rail"
      className="rounded-lg bg-surface-booth p-5 text-foreground-booth border border-border-strong/20"
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold tracking-wide text-foreground-booth/80">
          FOCUS BOOTH STAGE
        </span>
        <span className="font-mono text-xs text-foreground-booth/70 tabular-nums">
          STANDBY
        </span>
      </div>

      <div className="aspect-video w-full rounded-md bg-surface-booth-elevated border border-white/10 flex flex-col items-center justify-center gap-2 text-center p-4">
        <Video className="h-6 w-6 text-foreground-booth/60" aria-hidden="true" />
        <p className="text-xs text-foreground-booth/70">
          Webcam preview &amp; frame capture (`/video/frame/`) will activate during live sessions.
        </p>
      </div>

      <div className="mt-4 space-y-2 border-t border-white/10 pt-4 text-xs">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-foreground-booth/80">
            <CheckCircle2 className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
            Face Presence
          </span>
          <span className="font-mono text-foreground-booth/70 tabular-nums">Awaiting stream</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-foreground-booth/80">
            <Eye className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
            Eye Contact &amp; Pose
          </span>
          <span className="font-mono text-foreground-booth/70 tabular-nums">Awaiting stream</span>
        </div>
      </div>
    </section>
  );
}

