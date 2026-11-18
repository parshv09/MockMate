import { useId } from "react";

export function FormField({
  label,
  name,
  type = "text",
  value,
  onChange,
  placeholder,
  autoComplete,
  error,
  hint,
  required = false,
  disabled = false,
  rightElement = null,
  className = "",
}) {
  const generatedId = useId();
  const inputId = name ? `field-${name}-${generatedId}` : generatedId;
  const errorId = `${inputId}-error`;
  const hintId = `${inputId}-hint`;

  const describedBy = [
    error ? errorId : null,
    hint && !error ? hintId : null,
  ]
    .filter(Boolean)
    .join(" ") || undefined;

  return (
    <div className={`space-y-1.5 ${className}`.trim()}>
      <label
        htmlFor={inputId}
        className="block text-sm font-medium text-foreground"
      >
        {label}
        {required ? <span className="ml-0.5 text-destructive" aria-hidden="true">*</span> : null}
      </label>

      <div className="relative">
        <input
          id={inputId}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={required}
          disabled={disabled}
          aria-invalid={error ? "true" : "false"}
          aria-describedby={describedBy}
          className={`block w-full rounded-md border bg-surface px-3.5 py-2.5 text-sm text-foreground placeholder:text-foreground-muted transition-colors focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60 ${
            rightElement ? "pr-11" : ""
          } ${
            error
              ? "border-destructive focus:border-destructive focus:ring-destructive/20"
              : "border-border-strong focus:border-primary"
          }`}
        />
        {rightElement ? (
          <div className="absolute inset-y-0 right-0 flex items-center pr-2.5">
            {rightElement}
          </div>
        ) : null}
      </div>

      {error ? (
        <p id={errorId} role="alert" className="text-xs font-medium text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-xs text-foreground-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

