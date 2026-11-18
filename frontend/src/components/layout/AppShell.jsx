import { Outlet } from "react-router-dom";
import { SidebarNav } from "./SidebarNav.jsx";

export function AppShell() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <a
        href="#main-workspace"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
      >
        Skip to main content
      </a>

      <div className="flex min-h-screen flex-col lg:flex-row">
        <SidebarNav />
        <main id="main-workspace" className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div className="mx-auto max-w-studio">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

