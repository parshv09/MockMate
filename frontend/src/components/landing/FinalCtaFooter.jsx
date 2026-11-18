import { Link } from "react-router-dom";
import { ArrowRight, Radio } from "lucide-react";
import { Reveal } from "./MotionPrimitives.jsx";

export function FinalCtaFooter() {
  return (
    <>
      <section
        aria-labelledby="final-cta-heading"
        className="relative overflow-hidden bg-gradient-to-br from-[#070D19] via-[#0F1D3A] to-[#1E3A8A] py-20 text-white sm:py-24"
      >
        <div aria-hidden="true" className="pointer-events-none absolute -left-20 top-0 h-80 w-80 rounded-full bg-secondary/25 blur-3xl animate-pulse-glow" />
        <Reveal className="relative mx-auto max-w-3xl px-4 text-center sm:px-6">
          <h2 id="final-cta-heading" className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Your next opportunity starts with better preparation.
          </h2>
          <div className="mt-8">
            <Link
              to="/sessions/new"
              className="group inline-flex min-h-[52px] items-center justify-center gap-2 rounded-md bg-white px-8 py-3 text-base font-semibold text-slate-900 shadow-lg transition-all duration-150 hover:bg-slate-100 active:scale-[0.99]"
            >
              <span>Start Practicing</span>
              <ArrowRight className="h-4 w-4 transition-transform duration-150 group-hover:translate-x-0.5" aria-hidden="true" />
            </Link>
          </div>
        </Reveal>
      </section>

      <footer className="bg-[#070D19] py-8 text-slate-400">
        <div className="mx-auto flex max-w-studio flex-col items-center justify-between gap-4 px-4 text-sm sm:flex-row sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-2 font-display font-bold text-white">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary">
              <Radio className="h-3.5 w-3.5" aria-hidden="true" />
            </span>
            MockMate
          </Link>
          <nav aria-label="Footer" className="flex items-center gap-5">
            <a href="#features" className="hover:text-white">Features</a>
            <a href="#how-it-works" className="hover:text-white">How it works</a>
            <Link to="/login" className="hover:text-white">Sign in</Link>
          </nav>
          <p>© {new Date().getFullYear()} MockMate</p>
        </div>
      </footer>
    </>
  );
}

