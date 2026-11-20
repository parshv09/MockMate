import { Outlet } from "react-router-dom";

export function InterviewBoothLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-[#F8FAFC] text-foreground">
      <a
        href="#interview-main-stage"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
      >
        Skip to interview question
      </a>
      <Outlet />
    </div>
  );
}
