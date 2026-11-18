const TONE_CLASSES = {
  neutral: "bg-surface-subtle text-foreground-secondary border-border",
  primary: "bg-primary-subtle text-primary border-primary/20",
  teal: "bg-secondary-subtle text-secondary border-secondary/20",
  success: "bg-success-bg text-success border-success/20",
  warning: "bg-warning-bg text-warning border-warning/20",
  destructive: "bg-destructive-bg text-destructive border-destructive/20",
};

export function Badge({ tone = "neutral", className = "", children }) {
  const toneStyle = TONE_CLASSES[tone] || TONE_CLASSES.neutral;
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-sm border px-2.5 py-0.5 text-xs font-medium ${toneStyle} ${className}`.trim()}
    >
      {children}
    </span>
  );
}

