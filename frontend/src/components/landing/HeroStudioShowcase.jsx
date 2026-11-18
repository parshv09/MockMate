import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Play, Mic, Sparkles, CheckCircle2, Users } from "lucide-react";
import { Reveal, AnimatedNumber } from "./MotionPrimitives.jsx";

const CANDIDATE_PORTRAIT_URL =
  "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=900&q=80";

const WAVE_BARS = [0.4, 0.7, 0.95, 0.55, 0.85, 1, 0.5, 0.8, 0.6, 0.9, 0.45, 0.75, 0.95, 0.55, 0.7, 0.4];

export function HeroStudioShowcase() {
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <section
      aria-labelledby="hero-heading"
      className="relative overflow-hidden bg-gradient-to-b from-[#070D19] via-[#0B1528] to-[#0F1D3A] py-14 text-white sm:py-20 lg:py-24"
    >
      <div aria-hidden="true" className="pointer-events-none absolute -left-24 top-10 h-96 w-96 rounded-full bg-primary/25 blur-3xl animate-pulse-glow" />
      <div aria-hidden="true" className="pointer-events-none absolute -right-16 bottom-0 h-96 w-96 rounded-full bg-secondary/20 blur-3xl animate-pulse-glow" />

      <div className="relative mx-auto max-w-studio px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 items-center gap-14 lg:grid-cols-12 lg:gap-10">
          <Reveal className="space-y-6 lg:col-span-6">
            <h1
              id="hero-heading"
              className="font-display text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-[3.2rem] lg:leading-[1.1]"
            >
              Walk into your next interview with confidence.
            </h1>

            <p className="max-w-[52ch] text-base leading-relaxed text-slate-300 sm:text-lg">
              Practice realistic interviews, receive personalized AI feedback, and discover how to
              improve your answers before the real opportunity arrives.
            </p>

            <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:items-center">
              <Link
                to="/sessions/new"
                className="group inline-flex min-h-[52px] items-center justify-center gap-2 rounded-md bg-primary px-7 py-3 text-base font-semibold text-white shadow-lg transition-all duration-150 hover:bg-primary-hover active:scale-[0.99]"
              >
                <span>Start Practicing</span>
                <ArrowRight className="h-4 w-4 transition-transform duration-150 group-hover:translate-x-0.5" aria-hidden="true" />
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex min-h-[52px] items-center justify-center gap-2 rounded-md border border-white/25 px-6 py-3 text-base font-medium text-white transition-colors duration-150 hover:bg-white/10"
              >
                <Play className="h-4 w-4 text-teal-300" aria-hidden="true" />
                <span>See How It Works</span>
              </a>
            </div>

            <p className="flex items-center gap-2 text-sm text-slate-400">
              <Users className="h-4 w-4 text-teal-300" aria-hidden="true" />
              <span>For students, graduates, job seekers and working professionals.</span>
            </p>
          </Reveal>

          {/* Product visual */}
          <Reveal className="relative lg:col-span-6" direction="right" delayMs={120}>
            <div className="relative mx-auto max-w-xl">
              <div className="overflow-hidden rounded-2xl border border-white/15 bg-[#0C1630] shadow-2xl">
                <div className="relative aspect-[4/3] w-full bg-slate-900">
                  {!imageFailed ? (
                    <img
                      src={CANDIDATE_PORTRAIT_URL}
                      alt="A candidate practicing an interview in front of a laptop camera"
                      width="900"
                      height="675"
                      loading="eager"
                      onError={() => setImageFailed(true)}
                      className="h-full w-full object-cover object-top"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[#10204A] to-[#0B1528]">
                      <Mic className="h-12 w-12 text-teal-300" aria-hidden="true" />
                    </div>
                  )}
                  <div aria-hidden="true" className="absolute inset-0 bg-gradient-to-t from-[#070D19]/90 via-transparent to-transparent" />

                  <div className="absolute left-4 top-4 inline-flex items-center gap-2 rounded-full bg-black/55 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm">
                    <span className="h-2 w-2 rounded-full bg-rose-500" aria-hidden="true" />
                    Practice session
                  </div>

                  <div className="absolute inset-x-4 bottom-4">
                    <p className="text-sm font-semibold leading-snug text-white sm:text-base">
                      &ldquo;Tell me about a time you led a team through a tough deadline.&rdquo;
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 border-t border-white/10 bg-[#0A1226] px-4 py-3.5">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-white">
                    <Mic className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div aria-hidden="true" className="flex h-8 flex-1 items-center gap-1">
                    {WAVE_BARS.map((scale, idx) => (
                      <span
                        key={idx}
                        style={{ height: `${Math.round(scale * 28)}px`, animationDelay: `${idx * 70}ms` }}
                        className="animate-wave-bar w-1.5 rounded-full bg-gradient-to-t from-primary to-teal-300"
                      />
                    ))}
                  </div>
                  <span className="font-mono text-xs text-slate-300 tabular-nums">00:42</span>
                </div>
              </div>

              {/* Floating feedback card */}
              <div className="animate-float-slow mt-4 rounded-xl bg-white p-4 text-slate-900 shadow-2xl sm:absolute sm:-bottom-8 sm:-left-8 sm:mt-0 sm:w-64">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-900">
                    <Sparkles className="h-4 w-4 text-secondary" aria-hidden="true" />
                    AI feedback
                  </span>
                  <span className="font-mono text-lg font-bold text-primary tabular-nums">
                    <AnimatedNumber value={86} />
                    <span className="text-xs font-medium text-slate-500">/100</span>
                  </span>
                </div>
                <p className="mt-2 flex items-start gap-1.5 text-xs leading-relaxed text-slate-700">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-secondary" aria-hidden="true" />
                  <span>Clear example. Add the result you achieved to make it stronger.</span>
                </p>
                <p className="mt-2 text-[11px] text-slate-500">Illustrative example</p>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
