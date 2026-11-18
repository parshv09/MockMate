import { FileText, Mic, Sparkles, BarChart3, CheckCircle2, Type } from "lucide-react";
import { Reveal, AnimatedBar } from "./MotionPrimitives.jsx";

function PersonalizedVisual() {
  return (
    <div className="rounded-xl bg-white p-4 shadow-md">
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
        <FileText className="h-4 w-4 text-secondary" aria-hidden="true" />
        Your resume
      </div>
      <div aria-hidden="true" className="mt-3 space-y-2">
        <div className="h-2 w-4/5 rounded bg-slate-200" />
        <div className="h-2 w-full rounded bg-slate-200" />
        <div className="h-2 w-3/5 rounded bg-teal-200" />
      </div>
      <div className="mt-4 rounded-lg bg-teal-50 p-3 text-xs font-medium leading-relaxed text-teal-900">
        &ldquo;You led a student team of 12. How did you keep everyone on track?&rdquo;
      </div>
    </div>
  );
}

function PracticeVisual() {
  return (
    <div className="rounded-xl bg-white p-4 shadow-md">
      <div className="flex gap-2 text-xs font-semibold">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1 text-white">
          <Mic className="h-3 w-3" aria-hidden="true" /> Voice
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-slate-600">
          <Type className="h-3 w-3" aria-hidden="true" /> Text
        </span>
      </div>
      <div aria-hidden="true" className="mt-4 flex h-10 items-center gap-1">
        {[0.4, 0.8, 0.55, 1, 0.65, 0.9, 0.5, 0.85, 0.6, 0.75, 0.45, 0.9].map((scale, idx) => (
          <span
            key={idx}
            style={{ height: `${Math.round(scale * 36)}px`, animationDelay: `${idx * 80}ms` }}
            className="animate-wave-bar w-1.5 rounded-full bg-primary/80"
          />
        ))}
      </div>
    </div>
  );
}

function FeedbackVisual() {
  return (
    <div className="rounded-xl bg-white p-4 shadow-md">
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
        <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
        Suggestion
      </div>
      <p className="mt-3 text-xs leading-relaxed text-slate-700">
        Great start. Try opening with the result, then explain how you got there.
      </p>
      <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-emerald-700">
        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> Clear and well structured
      </p>
    </div>
  );
}

function InsightsVisual() {
  const rows = [
    { label: "Clarity", value: 88, color: "bg-primary" },
    { label: "Relevance", value: 82, color: "bg-secondary" },
    { label: "Structure", value: 74, color: "bg-primary" },
  ];
  return (
    <div className="rounded-xl bg-white p-4 shadow-md">
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>{row.label}</span>
              <span className="font-mono tabular-nums">{row.value}%</span>
            </div>
            <AnimatedBar value={row.value} trackClassName="mt-1 bg-slate-100" className={row.color} />
          </div>
        ))}
      </div>
      <p className="mt-3 text-[11px] text-slate-500">Illustrative example</p>
    </div>
  );
}

const FEATURES = [
  {
    icon: FileText,
    title: "Personalized Questions",
    text: "Practice questions based on your resume, target role and job description.",
    Visual: PersonalizedVisual,
  },
  {
    icon: Mic,
    title: "Voice & Text Practice",
    text: "Answer naturally using voice recording or written responses.",
    Visual: PracticeVisual,
  },
  {
    icon: Sparkles,
    title: "AI-Powered Feedback",
    text: "Understand your answer quality and receive actionable suggestions.",
    Visual: FeedbackVisual,
  },
  {
    icon: BarChart3,
    title: "Performance Insights",
    text: "Discover your strengths and identify areas for improvement.",
    Visual: InsightsVisual,
  },
];

export function FeatureBentoSection() {
  return (
    <section
      id="features"
      aria-labelledby="features-heading"
      className="bg-gradient-to-b from-slate-50 to-white py-16 sm:py-24"
    >
      <div className="mx-auto max-w-studio px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 id="features-heading" className="font-display text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Everything you need to prepare with purpose
          </h2>
          <p className="mt-3 text-base text-slate-600">
            Realistic practice, honest feedback, and a clear path to improve.
          </p>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-x-10 gap-y-14 md:grid-cols-2">
          {FEATURES.map((feature, idx) => {
            const Icon = feature.icon;
            const Visual = feature.Visual;
            return (
              <Reveal key={feature.title} delayMs={(idx % 2) * 100}>
                <div className="flex h-full flex-col gap-5 rounded-2xl bg-gradient-to-br from-blue-50 via-slate-50 to-teal-50 p-6 transition-shadow duration-200 hover:shadow-md sm:p-7">
                  <Visual />
                  <div>
                    <h3 className="flex items-center gap-2.5 font-display text-xl font-bold text-slate-900">
                      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white">
                        <Icon className="h-4 w-4" aria-hidden="true" />
                      </span>
                      {feature.title}
                    </h3>
                    <p className="mt-2 text-base leading-relaxed text-slate-600">{feature.text}</p>
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
