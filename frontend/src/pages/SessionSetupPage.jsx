import { Link } from "react-router-dom";
import { ArrowLeft, PlayCircle } from "lucide-react";
import { Button } from "../components/ui/Button.jsx";
import { InterviewSetup } from "../components/sessions/InterviewSetup.jsx";

export function SessionSetupPage() {
  return (
    <div className="space-y-6">
      {/* Studio Header Banner */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#070D19] via-[#0B1528] to-[#0F1D3A] p-6 text-white shadow-lg sm:p-8">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-primary/25 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-20 left-1/3 h-56 w-56 rounded-full bg-secondary/20 blur-3xl"
        />

        <div className="relative flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-teal-300">
              <PlayCircle className="h-3.5 w-3.5" aria-hidden="true" />
              Session Setup
            </span>
            <h1 className="font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Start a New Interview
            </h1>
            <p className="max-w-xl text-sm text-slate-300">
              Choose between standard role practice or a personalized interview tailored to your resume and target job description.
            </p>
          </div>

          <Link to="/dashboard" className="shrink-0">
            <Button
              variant="secondary"
              size="sm"
              className="border-white/20 bg-white/10 text-white hover:bg-white/20"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              <span>Back to Dashboard</span>
            </Button>
          </Link>
        </div>
      </section>

      <InterviewSetup />
    </div>
  );
}
