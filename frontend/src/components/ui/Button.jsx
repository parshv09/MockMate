const VARIANT_CLASSES = {
  primary:
    "bg-primary text-primary-foreground hover:bg-primary-hover border border-transparent shadow-xs",
  secondary:
    "bg-surface text-foreground hover:bg-surface-subtle border border-border-strong",
  ghost:
    "bg-transparent text-foreground-secondary hover:bg-surface-subtle border border-transparent",
  destructive:
    "bg-destructive text-destructive-foreground hover:opacity-95 border border-transparent",
};

const SIZE_CLASSES = {
  sm: "min-h-[36px] px-3 py-1.5 text-xs",
  md: "min-h-[44px] sm:min-h-[40px] px-4 py-2 text-sm",
  lg: "min-h-[48px] px-6 py-2.5 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
  type = "button",
  isLoading = false,
  disabled = false,
  className = "",
  children,
  ...props
}) {
  const variantStyle = VARIANT_CLASSES[variant] || VARIANT_CLASSES.primary;
  const sizeStyle = SIZE_CLASSES[size] || SIZE_CLASSES.md;

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      aria-busy={isLoading ? "true" : undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${variantStyle} ${sizeStyle} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
}

