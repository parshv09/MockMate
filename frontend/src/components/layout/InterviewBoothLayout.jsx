import { Link, Outlet } from "react-router-dom";
import { ArrowLeft, Radio } from "lucide-react";

export function InterviewBoothLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="border-b border-border bg-surface px-4 sm:px-6">
        <div className="mx-auto flex h-14 max-w-studio items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/dashboard"
              className="inline-flex min-h-[36px] items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium text-foreground-secondary hover:bg-surface-subtle hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              <span>Exit Booth</span>
            </Link>
            <div className="h-4 w-px bg-border" aria-hidden="true" />
            <div className="flex items-center gap-2">
              <Radio className="h-4 w-4 text-primary" aria-hidden="true" />
              <span className="text-sm font-semibold text-foreground">Focus Booth Workspace</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="font-mono text-xs font-medium text-foreground-muted tabular-nums">
              QUESTION 01 / 05
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-studio flex-1 px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}

