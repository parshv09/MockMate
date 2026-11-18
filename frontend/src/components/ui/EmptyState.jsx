export function EmptyState({
  icon: Icon = null,
  title,
  description,
  action = null,
  className = "",
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/70 px-6 py-12 text-center ${className}`.trim()}
    >
      {Icon ? (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary-subtle text-secondary">
          <Icon className="h-6 w-6" aria-hidden="true" />
        </div>
      ) : null}
      {title ? (
        <h2 className="mt-4 font-display text-base font-bold text-slate-900">{title}</h2>
      ) : null}
      {description ? (
        <p className="mt-1 max-w-md text-sm text-slate-600">{description}</p>
      ) : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

