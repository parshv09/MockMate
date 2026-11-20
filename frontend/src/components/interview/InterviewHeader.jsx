import { Link } from "react-router-dom";
import { ArrowLeft, FileText, PhoneOff, Radio } from "lucide-react";
import { getSessionDisplayTitle } from "../../utils/sessionHistory.js";
import { Button } from "../ui/Button.jsx";

export function InterviewHeader({
  session,
  currentIndex = 1,
  totalQuestions = 0,
  answeredCount = 0,
  isAvatarConnected = false,
  isBusy = false,
  onRequestEndInterview,
}) {
  const title = getSessionDisplayTitle(session);
  const isCompleted = Boolean(session?.completed || session?.is_completed);
  const safeTotal = Math.max(0, Number(totalQuestions) || 0);
  const safeIndex = safeTotal > 0 ? Math.min(Math.max(1, currentIndex), safeTotal) : 1;

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-[#070D19]/95 text-white backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
        {/* Left: Brand + Exit + Role Title */}
        <div className="flex min-w-0 items-center gap-3">
          <Link
            to="/dashboard"
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-white/15 bg-white/5 px-2.5 text-xs font-medium text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">Exit</span>
          </Link>

          <div className="flex min-w-0 items-center gap-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-white">
              <Radio className="h-3.5 w-3.5" aria-hidden="true" />
            </span>
            <span className="truncate font-display text-sm font-bold text-white">
              {title}
            </span>
            {session?.resume_title ? (
              <span className="hidden items-center gap-1 rounded-full border border-teal-400/25 bg-teal-500/10 px-2 py-0.5 text-[11px] font-medium text-teal-300 md:inline-flex">
                <FileText className="h-3 w-3" aria-hidden="true" />
                <span>{session.resume_title}</span>
              </span>
            ) : null}
          </div>
        </div>

        {/* Right: Compact Progress, Connection Status & End Interview */}
        <div className="flex shrink-0 items-center gap-2.5">
          {safeTotal > 0 ? (
            <div className="flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs">
              <span className="font-semibold text-white">
                Question {safeIndex} of {safeTotal}
              </span>
              <span className="text-slate-500" aria-hidden="true">
                ·
              </span>
              <span
                aria-label="Completed question count"
                className="font-mono text-[11px] text-slate-300 tabular-nums"
              >
                {answeredCount} / {safeTotal}
              </span>
            </div>
          ) : null}

          <span
            className={`hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium sm:inline-flex ${
              isAvatarConnected
                ? "border-emerald-400/30 bg-emerald-500/15 text-emerald-300"
                : "border-white/15 bg-white/5 text-slate-300"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isAvatarConnected ? "bg-emerald-400" : "bg-teal-400"
              }`}
              aria-hidden="true"
            />
            {isAvatarConnected ? "Live Video" : "Voice Studio"}
          </span>

          {!isCompleted ? (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              disabled={isBusy}
              onClick={onRequestEndInterview}
            >
              <PhoneOff className="h-3.5 w-3.5" aria-hidden="true" />
              <span>End Interview</span>
            </Button>
          ) : null}
        </div>
      </div>
    </header>
  );
}
