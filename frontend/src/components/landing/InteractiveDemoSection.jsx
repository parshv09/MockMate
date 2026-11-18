import { useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, Sliders, CheckCircle2, Lightbulb, ArrowRight } from "lucide-react";
import { Reveal, AnimatedNumber, AnimatedBar } from "./MotionPrimitives.jsx";

const DEMO_MODES = {
  standard: {
    label: "Standard Interview",
    icon: Sliders,
    intro: "General questions for the role you choose.",
    questions: [
      {
        id: "s1",
        short: "Strengths",
        question: "What would you say is your greatest strength?",
        answer:
          "I'm good at breaking big tasks into small steps. In my final-year project I split the work across four people and we finished a week early.",
        score: 84,
        strengths: "Specific example with a clear outcome.",
        tip: "Connect the strength to the role you are applying for.",
      },
      {
        id: "s2",
        short: "Teamwork",
        question: "Tell me about a time you disagreed with a teammate.",
        answer:
          "We disagreed on the design approach. I suggested we each test our idea for a day, then chose the option the data supported.",
        score: 88,
        strengths: "Calm tone and a fair way to resolve the conflict.",
        tip: "Mention what you learned from the experience.",
      },
      {
        id: "s3",
        short: "Pressure",
        question: "How do you handle tight deadlines?",
        answer:
          "I list priorities first, ask early if something is unclear, and update my team regularly so there are no surprises.",
        score: 79,
        strengths: "Shows planning and communication.",
        tip: "Add a short real example to make it memorable.",
      },
    ],
  },
  resume: {
    label: "Resume + JD Interview",
    icon: Sparkles,
    intro: "Questions built from your resume and the job description.",
    questions: [
      {
        id: "r1",
        short: "Leadership",
        question:
          "Your resume mentions leading a campus event team of 12. How would that help you as a Project Coordinator?",
        answer:
          "Running the event taught me to assign clear owners and check in daily. I'd bring the same approach to coordinating project timelines.",
        score: 90,
        strengths: "Links past experience directly to the new role.",
        tip: "Share one measurable result, like attendance or budget.",
      },
      {
        id: "r2",
        short: "Skills match",
        question:
          "The job asks for strong reporting skills. Where have you shown this in your internship?",
        answer:
          "During my internship I prepared weekly summaries for my manager and built a simple dashboard that saved the team about two hours each week.",
        score: 86,
        strengths: "Relevant example that matches the job description.",
        tip: "Describe the tools you used in a sentence.",
      },
      {
        id: "r3",
        short: "Motivation",
        question: "Why does this role fit the direction of your career?",
        answer:
          "My projects have all involved organizing people and plans, and this role lets me do that every day while growing into management.",
        score: 82,
        strengths: "Genuine and consistent with your background.",
        tip: "Mention something specific about the company.",
      },
    ],
  },
};

export function InteractiveDemoSection() {
  const [modeKey, setModeKey] = useState("resume");
  const [questionIdx, setQuestionIdx] = useState(0);

  const mode = DEMO_MODES[modeKey];
  const current = mode.questions[questionIdx];

  const switchMode = (key) => {
    setModeKey(key);
    setQuestionIdx(0);
  };

  return (
    <section
      id="demo"
      aria-labelledby="demo-heading"
      className="relative overflow-hidden bg-gradient-to-b from-[#0B1528] to-[#0F1D3A] py-16 text-white sm:py-24"
    >
      <div aria-hidden="true" className="pointer-events-none absolute -right-20 top-10 h-80 w-80 rounded-full bg-secondary/20 blur-3xl animate-pulse-glow" />
      <div className="relative mx-auto max-w-studio px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 id="demo-heading" className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Try it before you sign up
          </h2>
          <p className="mt-3 text-base text-slate-300">
            Pick an interview type and see an example question, answer and feedback.
          </p>

          <div
            role="tablist"
            aria-label="Interview type"
            className="mt-7 inline-flex rounded-full bg-white/10 p-1"
          >
            {Object.entries(DEMO_MODES).map(([key, item]) => {
              const Icon = item.icon;
              const selected = key === modeKey;
              return (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  onClick={() => switchMode(key)}
                  className={`inline-flex min-h-[44px] items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors sm:px-5 ${
                    selected ? "bg-white text-slate-900" : "text-slate-200 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
          <p className="mt-3 text-sm text-slate-400">{mode.intro}</p>
        </Reveal>

        <Reveal delayMs={100} className="mt-10">
          <div className="mx-auto grid max-w-5xl grid-cols-1 overflow-hidden rounded-2xl bg-white text-slate-900 shadow-2xl lg:grid-cols-5">
            <div className="space-y-5 p-6 sm:p-8 lg:col-span-3">
              <div className="flex flex-wrap gap-2" role="group" aria-label="Sample questions">
                {mode.questions.map((q, idx) => (
                  <button
                    key={q.id}
                    type="button"
                    aria-pressed={idx === questionIdx}
                    onClick={() => setQuestionIdx(idx)}
                    className={`min-h-[40px] rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                      idx === questionIdx
                        ? "bg-primary text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {q.short}
                  </button>
                ))}
              </div>

              <div>
                <p className="text-sm font-semibold text-primary">Interview question</p>
                <h3 className="mt-1.5 font-display text-xl font-bold leading-snug sm:text-2xl">
                  {current.question}
                </h3>
              </div>

              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-600">Example answer</p>
                <p className="mt-1.5 text-base leading-relaxed text-slate-800">&ldquo;{current.answer}&rdquo;</p>
              </div>
            </div>

            <div className="space-y-5 bg-gradient-to-br from-blue-50 to-teal-50 p-6 sm:p-8 lg:col-span-2">
              <div className="flex items-center justify-between">
                <p className="font-display text-lg font-bold">AI feedback</p>
                <p className="font-mono text-3xl font-bold text-primary tabular-nums">
                  <AnimatedNumber value={current.score} />
                  <span className="text-sm font-medium text-slate-500">/100</span>
                </p>
              </div>

              <AnimatedBar value={current.score} trackClassName="bg-white" className="bg-gradient-to-r from-primary to-secondary" />

              <p className="flex items-start gap-2 text-base text-slate-800">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" aria-hidden="true" />
                <span>
                  <strong className="font-semibold">What worked: </strong>
                  {current.strengths}
                </span>
              </p>
              <p className="flex items-start gap-2 text-base text-slate-800">
                <Lightbulb className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
                <span>
                  <strong className="font-semibold">Try this: </strong>
                  {current.tip}
                </span>
              </p>

              <p className="text-xs text-slate-500">Illustrative example, not a real result.</p>

              <Link
                to="/sessions/new"
                className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-md bg-primary px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-primary-hover"
              >
                <span>Practice with your own resume</span>
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
