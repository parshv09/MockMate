import { Link, Outlet } from "react-router-dom";
import { ArrowLeft, Radio } from "lucide-react";

export function AuthLayout() {
  return (
    <div className="relative flex min-h-screen flex-col justify-between overflow-hidden bg-gradient-to-b from-[#070D19] via-[#0B1528] to-[#0F1D3A] text-white">
      {/* Ambient radial glows matching Landing Hero */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-24 top-16 h-96 w-96 rounded-full bg-primary/25 blur-3xl animate-pulse-glow"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-20 bottom-10 h-96 w-96 rounded-full bg-secondary/20 blur-3xl animate-pulse-glow"
      />

      <header className="relative z-10 border-b border-white/10 bg-[#070D19]/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-studio items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link
            to="/"
            className="flex items-center gap-2.5 font-display text-lg font-bold tracking-tight text-white"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-white">
              <Radio className="h-4 w-4" aria-hidden="true" />
            </span>
            <span>MockMate</span>
          </Link>

          <Link
            to="/"
            className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-white/10 hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Back to Home</span>
          </Link>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex w-full max-w-lg flex-1 flex-col justify-center px-4 py-10 sm:px-6">
        <Outlet />
      </main>

      <footer className="relative z-10 border-t border-white/10 bg-[#070D19]/60 py-4 text-center text-xs text-slate-400">
        MockMate — AI Interview Preparation Studio
      </footer>
    </div>
  );
}
