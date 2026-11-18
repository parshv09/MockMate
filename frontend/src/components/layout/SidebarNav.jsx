import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  PlayCircle,
  Radio,
  X,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext.jsx";
import { useToast } from "../../context/ToastContext.jsx";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/sessions/new", label: "Start Interview", icon: PlayCircle },
  { to: "/resumes", label: "Resume Vault", icon: FileText },
];

function getUserDisplayName(user) {
  if (!user) return "Candidate";
  const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  return fullName || user.username || "Candidate";
}

function getUserTypeLabel(userType) {
  if (userType === "job_seeker") return "Job Seeker";
  return "Student";
}

export function SidebarNav() {
  const { user, logout } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const displayName = getUserDisplayName(user);
  const userTypeLabel = getUserTypeLabel(user?.user_type);

  function handleLogout() {
    logout();
    setMobileOpen(false);
    showToast({
      title: "Signed out",
      description: "You have been signed out of MockMate.",
      tone: "info",
    });
    navigate("/login", { replace: true });
  }

  return (
    <>
      {/* Mobile Header & Drawer (matching LandingNavbar dark navy chrome) */}
      <header className="sticky top-0 z-30 border-b border-white/10 bg-[#070D19]/95 text-slate-100 backdrop-blur-md lg:hidden">
        <div className="flex h-16 items-center justify-between px-4 sm:px-6">
          <NavLink
            to="/dashboard"
            onClick={() => setMobileOpen(false)}
            className="flex items-center gap-2.5 font-display text-lg font-bold tracking-tight text-white"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-white">
              <Radio className="h-4 w-4" aria-hidden="true" />
            </span>
            <span>MockMate</span>
          </NavLink>

          <button
            type="button"
            onClick={() => setMobileOpen((prev) => !prev)}
            aria-expanded={mobileOpen}
            aria-controls="mobile-studio-nav"
            aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-white/15 bg-white/5 text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
          >
            {mobileOpen ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </div>

        {mobileOpen ? (
          <div
            id="mobile-studio-nav"
            className="border-t border-white/10 bg-[#0A1122] px-4 py-4 shadow-xl"
          >
            <nav aria-label="Mobile Studio Navigation" className="space-y-1">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) =>
                      `flex min-h-[44px] items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors ${
                        isActive
                          ? "bg-primary text-white shadow-sm"
                          : "text-slate-300 hover:bg-white/10 hover:text-white"
                      }`
                    }
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>

            <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{displayName}</p>
                <p className="truncate text-xs text-slate-400">
                  {user?.target_role ? `${user.target_role} · ` : ""}
                  {userTypeLabel}
                </p>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex min-h-[40px] items-center gap-1.5 rounded-md border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
              >
                <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Sign out</span>
              </button>
            </div>
          </div>
        ) : null}
      </header>

      {/* Desktop Sidebar (Deep Navy Studio Rail matching Landing aesthetic) */}
      <aside
        aria-label="Primary Studio Navigation"
        className="hidden lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-64 lg:shrink-0 lg:flex-col lg:justify-between lg:border-r lg:border-white/10 lg:bg-gradient-to-b lg:from-[#070D19] lg:via-[#0A1324] lg:to-[#0E1A33] lg:text-slate-100"
      >
        <div>
          <div className="flex h-16 items-center justify-between border-b border-white/10 px-6">
            <NavLink
              to="/dashboard"
              className="flex items-center gap-2.5 font-display text-lg font-bold tracking-tight text-white"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-white">
                <Radio className="h-4 w-4" aria-hidden="true" />
              </span>
              <span>MockMate</span>
            </NavLink>
            <span className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 font-mono text-[10px] font-medium tracking-wider text-teal-300">
              STUDIO
            </span>
          </div>

          <nav className="space-y-1.5 p-4">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex min-h-[44px] items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-primary text-white shadow-sm"
                        : "text-slate-300 hover:bg-white/10 hover:text-white"
                    }`
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        <div className="border-t border-white/10 p-4">
          <div className="rounded-xl border border-white/10 bg-white/5 p-3.5">
            <p className="truncate text-sm font-semibold text-white">{displayName}</p>
            <p className="truncate text-xs text-slate-300">
              {user?.target_role ? user.target_role : userTypeLabel}
            </p>
            {user?.username ? (
              <p className="mt-1 truncate font-mono text-[11px] text-teal-300/90">
                @{user.username}
              </p>
            ) : null}
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="mt-2.5 flex w-full min-h-[40px] items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
    </>
  );
}
