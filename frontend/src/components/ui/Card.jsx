export function Card({ className = "", children, ...props }) {
  return (
    <div
      className={`rounded-lg border border-border bg-surface p-4 sm:p-6 ${className}`.trim()}
      {...props}
    >
      {children}
    </div>
  );
}

