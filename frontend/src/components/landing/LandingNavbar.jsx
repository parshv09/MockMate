import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Radio, Menu, X, ArrowRight } from "lucide-react";

const NAV_LINKS = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#demo", label: "Try a demo" },
  { href: "#insights", label: "Insights" },
];

export function LandingNavbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!mobileMenuOpen) {
      return undefined;
    }
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileMenuOpen]);

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#070D19]/90 text-slate-100 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-studio items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link
          to="/"
          className="flex items-center gap-2.5 rounded-md font-display text-lg font-bold tracking-tight text-white"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-white">
            <Radio className="h-4 w-4" aria-hidden="true" />
          </span>
          <span>MockMate</span>
        </Link>

        <nav aria-label="Page sections" className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded-md px-3.5 py-2 text-sm font-medium text-slate-300 transition-colors duration-150 hover:bg-white/10 hover:text-white"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2.5 md:flex">
          <Link
            to="/login"
            className="inline-flex min-h-[40px] items-center rounded-md px-3.5 py-2 text-sm font-medium text-slate-200 transition-colors duration-150 hover:bg-white/10 hover:text-white"
          >
            Sign in
          </Link>
          <Link
            to="/sessions/new"
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-hover active:scale-[0.99]"
          >
            <span>Start Practicing</span>
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-navigation-drawer"
          aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md border border-white/15 bg-white/5 text-slate-200 hover:bg-white/10 md:hidden"
        >
          {mobileMenuOpen ? (
            <X className="h-5 w-5" aria-hidden="true" />
          ) : (
            <Menu className="h-5 w-5" aria-hidden="true" />
          )}
        </button>
      </div>

      {mobileMenuOpen ? (
        <nav
          id="mobile-navigation-drawer"
          aria-label="Mobile navigation"
          className="border-t border-white/10 bg-[#0A1122] px-4 py-4 md:hidden"
        >
          <div className="flex flex-col gap-1">
            {NAV_LINKS.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className="flex min-h-[44px] items-center rounded-md px-3 text-sm font-medium text-slate-200 hover:bg-white/10 hover:text-white"
              >
                {item.label}
              </a>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 border-t border-white/10 pt-4">
            <Link
              to="/login"
              onClick={() => setMobileMenuOpen(false)}
              className="inline-flex min-h-[44px] items-center justify-center rounded-md border border-white/20 px-4 py-2 text-sm font-medium text-slate-100 hover:bg-white/10"
            >
              Sign in
            </Link>
            <Link
              to="/sessions/new"
              onClick={() => setMobileMenuOpen(false)}
              className="inline-flex min-h-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
            >
              Start Practicing
            </Link>
          </div>
        </nav>
      ) : null}
    </header>
  );
}
