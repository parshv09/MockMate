export function SessionSummarySkeleton() {
  return (
    <div
      className="space-y-6 animate-pulse"
      aria-label="Loading interview performance report"
    >
      {/* Header Skeleton */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2">
            <div className="h-4 w-48 rounded-md bg-slate-200" />
            <div className="h-8 w-72 rounded-md bg-slate-200" />
            <div className="h-4 w-40 rounded-md bg-slate-200" />
          </div>
          <div className="flex items-center gap-2">
            <div className="h-10 w-32 rounded-md bg-slate-200" />
            <div className="h-10 w-40 rounded-md bg-slate-200" />
          </div>
        </div>
      </div>

      {/* KPI Overview Skeleton */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
          <div className="flex flex-col items-center justify-center md:col-span-5">
            <div className="h-36 w-36 rounded-full bg-slate-200" />
            <div className="mt-3 h-4 w-28 rounded-md bg-slate-200" />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:col-span-7">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 rounded-lg bg-slate-200" />
            ))}
          </div>
        </div>
      </div>

      {/* Feedback Section Skeleton */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="h-48 rounded-xl border border-border bg-surface p-6" />
        <div className="h-48 rounded-xl border border-border bg-surface p-6" />
      </div>

      {/* Accordion Questions Skeleton */}
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 rounded-xl border border-border bg-surface" />
        ))}
      </div>
    </div>
  );
}

