import { CheckCircle2, TrendingUp, Eye, UserCheck, Move } from "lucide-react";
import { Reveal, AnimatedNumber, AnimatedBar } from "./MotionPrimitives.jsx";

const ANSWER_QUALITY = [
  { label: "Clarity", value: 88, color: "bg-primary" },
  { label: "Relevance", value: 84, color: "bg-secondary" },
  { label: "Structure", value: 76, color: "bg-primary" },
  { label: "Examples", value: 72, color: "bg-secondary" },
];

const BEHAVIOR = [
  { icon: UserCheck, label: "Stayed in frame", value: 95 },
  { icon: Eye, label: "Eye contact", value: 82 },
  { icon: Move, label: "Steady posture", value: 88 },
];

const RING_CIRCUMFERENCE = 2 * Math.PI * 42;

export function AnalyticsReportPreview() {
  const overall = 84;

  return (
    <section
      id="insights"
      aria-labelledby="insights-heading"
      className="bg-gradient-to-b from-white to-slate-50 py-16 sm:py-24"
    >
      <div className="mx-auto max-w-studio px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 id="insights-heading" className="font-display text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            See exactly how you are improving
          </h2>
          <p className="mt-3 text-base text-slate-600">
            After every session you get a clear report with your score, strengths and next steps.
          </p>
        </Reveal>

        <Reveal delayMs={100} className="mt-12">
          <div className="mx-auto max-w-5xl rounded-2xl bg-white p-6 shadow-xl ring-1 ring-slate-200/70 sm:p-8">
            <p className="text-xs font-medium text-slate-500">Sample report. Illustrative data only.</p>

            <div className="mt-5 grid grid-cols-1 gap-8 lg:grid-cols-12">
              {/* Score ring */}
              <div className="flex flex-col items-center justify-center gap-3 lg:col-span-3">
                <div className="relative h-36 w-36">
                  <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" aria-hidden="true">
                    <circle cx="50" cy="50" r="42" fill="none" stroke="#E2E8F0" strokeWidth="9" />
                    <circle
                      cx="50"
                      cy="50"
                      r="42"
                      fill="none"
                      stroke="#1D4ED8"
                      strokeWidth="9"
                      strokeLinecap="round"
                      strokeDasharray={RING_CIRCUMFERENCE}
                      strokeDashoffset={RING_CIRCUMFERENCE * (1 - overall / 100)}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="font-mono text-4xl font-bold text-slate-900 tabular-nums">
                      <AnimatedNumber value={overall} />
                    </span>
                    <span className="text-xs font-medium text-slate-500">Overall score</span>
                  </div>
                </div>
                <p className="flex items-center gap-1.5 text-sm font-semibold text-emerald-700">
                  <TrendingUp className="h-4 w-4" aria-hidden="true" /> Interview ready
                </p>
              </div>

              {/* Answer quality */}
              <div className="lg:col-span-5">
                <h3 className="font-display text-lg font-bold text-slate-900">Answer quality</h3>
                <div className="mt-4 space-y-4">
                  {ANSWER_QUALITY.map((item) => (
                    <div key={item.label}>
                      <div className="flex justify-between text-sm font-medium text-slate-700">
                        <span>{item.label}</span>
                        <span className="font-mono tabular-nums">{item.value}%</span>
                      </div>
                      <AnimatedBar value={item.value} trackClassName="mt-1.5 bg-slate-100" className={item.color} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Strengths and improvements */}
              <div className="space-y-5 lg:col-span-4">
                <div>
                  <h3 className="font-display text-lg font-bold text-slate-900">Strengths</h3>
                  <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
                    <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />Clear and confident delivery</li>
                    <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />Answers match the role</li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-display text-lg font-bold text-slate-900">Areas to improve</h3>
                  <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
                    <li className="flex gap-2"><TrendingUp className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" />Add results and numbers to examples</li>
                    <li className="flex gap-2"><TrendingUp className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" />Keep answers under two minutes</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Behavioral insights */}
            <div className="mt-8 rounded-xl bg-gradient-to-r from-[#0B1528] to-[#12275A] p-5 text-white sm:p-6">
              <div className="flex flex-col justify-between gap-1 sm:flex-row sm:items-baseline">
                <h3 className="font-display text-lg font-bold">Behavioral insights</h3>
                <p className="text-xs text-slate-300">Estimates from your camera to help you practice. Not a judgment.</p>
              </div>
              <div className="mt-4 grid grid-cols-1 gap-5 sm:grid-cols-3">
                {BEHAVIOR.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.label}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="inline-flex items-center gap-2 text-slate-100">
                          <Icon className="h-4 w-4 text-teal-300" aria-hidden="true" />
                          {item.label}
                        </span>
                        <span className="font-mono text-xs text-slate-200 tabular-nums">{item.value}%</span>
                      </div>
                      <AnimatedBar value={item.value} trackClassName="mt-2 bg-white/15" className="bg-teal-300" />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
