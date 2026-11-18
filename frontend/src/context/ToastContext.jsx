import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

const ToastContext = createContext(null);

const TONE_STYLES = {
  success: {
    container: "border-success/25 bg-surface text-foreground",
    icon: CheckCircle2,
    iconColor: "text-success",
  },
  error: {
    container: "border-destructive/25 bg-surface text-foreground",
    icon: AlertCircle,
    iconColor: "text-destructive",
  },
  info: {
    container: "border-primary/25 bg-surface text-foreground",
    icon: Info,
    iconColor: "text-primary",
  },
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const showToast = useCallback(
    ({ title, description = "", tone = "info", duration = 4000 }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setToasts((prev) => [...prev, { id, title, description, tone }]);

      if (duration > 0) {
        window.setTimeout(() => {
          dismissToast(id);
        }, duration);
      }

      return id;
    },
    [dismissToast]
  );

  const value = useMemo(
    () => ({
      toasts,
      showToast,
      dismissToast,
    }),
    [toasts, showToast, dismissToast]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2 px-4 sm:px-0"
      >
        {toasts.map((toast) => {
          const style = TONE_STYLES[toast.tone] || TONE_STYLES.info;
          const Icon = style.icon;
          return (
            <div
              key={toast.id}
              role="status"
              className={`pointer-events-auto flex items-start gap-3 rounded-lg border p-3.5 shadow-md ${style.container}`}
            >
              <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${style.iconColor}`} aria-hidden="true" />
              <div className="min-w-0 flex-1">
                {toast.title ? (
                  <p className="text-sm font-semibold text-foreground">{toast.title}</p>
                ) : null}
                {toast.description ? (
                  <p className="mt-0.5 text-xs text-foreground-secondary">{toast.description}</p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                aria-label="Dismiss notification"
                className="rounded p-1 text-foreground-muted transition-colors hover:bg-surface-subtle hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
