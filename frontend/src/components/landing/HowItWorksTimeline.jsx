import { Upload, Mic, ClipboardCheck } from "lucide-react";
import { Reveal } from "./MotionPrimitives.jsx";

const STEPS = [
  {
    number: 1,
    icon: Upload,
    title: "Upload Your Resume",
    text: "Add your resume and the role you want, or start with a general interview.",
  },
  {
    number: 2,
    icon: Mic,
    title: "Practice Your Interview",
    text: "Answer realistic questions out loud or in writing, at your own pace.",
  },
  {
    number: 3,
    icon: ClipboardCheck,
    title: "Review Your Feedback",
    text: "See what worked, what to improve, and how your answers stack up.",
  },
];

export function HowItWorksTimeline() {
  return (
    <section id="how-it-works" aria-labelledby="how-it-works-heading" className="bg-white py-16 sm:py-24">
      <div className="mx-auto max-w-studio px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 id="how-it-works-heading" className="font-display text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            How it works
          </h2>
          <p className="mt-3 text-base text-slate-600">Three simple steps from first answer to real progress.</p>
        </Reveal>

        <div className="relative mt-14">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-[16.6%] right-[16.6%] top-8 hidden h-0.5 bg-gradient-to-r from-primary/60 via-secondary/60 to-primary/60 md:block"
          />
          <ol className="grid grid-cols-1 gap-10 md:grid-cols-3 md:gap-6">
            {STEPS.map((step, idx) => {
              const Icon = step.icon;
              return (
                <li key={step.number}>
                  <Reveal delayMs={idx * 120} className="flex flex-col items-center text-center">
                    <div className="relative z-10 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[#2E5BE8] text-white shadow-lg ring-8 ring-white">
                      <Icon className="h-7 w-7" aria-hidden="true" />
                      <span className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-secondary font-mono text-xs font-bold text-white">
                        {step.number}
                      </span>
                    </div>
                    <h3 className="mt-5 font-display text-xl font-bold text-slate-900">{step.title}</h3>
                    <p className="mt-2 max-w-xs text-base leading-relaxed text-slate-600">{step.text}</p>
                  </Reveal>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </section>
  );
}
