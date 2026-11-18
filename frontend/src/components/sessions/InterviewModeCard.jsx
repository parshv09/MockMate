import { CheckCircle2 } from "lucide-react";

export function InterviewModeCard({
  icon: Icon,
  title,
  description,
  badgeText,
  selected = false,
  disabled = false,
  onSelect,
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      aria-pressed={selected}
      className={`group relative flex w-full flex-col items-start gap-3 rounded-2xl border p-5 text-left transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-60 ${
        selected
          ? "border-primary bg-primary-subtle/50 shadow-sm ring-1 ring-primary/20"
          : "border-slate-200/90 bg-white hover:border-slate-300 hover:shadow-sm"
      }`}
    >
      <div className="flex w-full items-center justify-between gap-2">
        <span
          className={`flex h-10 w-10 items-center justify-center rounded-xl transition-colors ${
            selected
              ? "bg-primary text-white"
              : "bg-slate-100 text-slate-700 group-hover:bg-primary-subtle group-hover:text-primary"
          }`}
        >
          {Icon ? <Icon className="h-5 w-5" aria-hidden="true" /> : null}
        </span>

        <div className="flex items-center gap-2">
          {badgeText ? (
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                selected
                  ? "bg-primary text-white"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              {badgeText}
            </span>
          ) : null}
          {selected ? (
            <CheckCircle2 className="h-5 w-5 text-primary" aria-hidden="true" />
          ) : null}
        </div>
      </div>

      <div>
        <h2 className="font-display text-base font-bold text-slate-900">
          {title}
        </h2>
        <p className="mt-1 text-sm leading-relaxed text-slate-600">
          {description}
        </p>
      </div>
    </button>
  );
}

