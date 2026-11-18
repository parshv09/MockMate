import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Radio } from "lucide-react";
import { useAuth } from "../../context/AuthContext.jsx";

export function ProtectedRoute() {
  const { isAuthenticated, isInitializing } = useAuth();
  const location = useLocation();

  if (isInitializing) {
    return (
      <div
        role="status"
        aria-label="Restoring session"
        className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-foreground"
      >
        <div className="flex items-center gap-3 rounded-lg border border-border bg-surface px-5 py-4 shadow-xs">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Radio className="h-4 w-4 animate-pulse" aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm font-semibold text-foreground">Restoring your studio...</p>
            <p className="text-xs text-foreground-muted">Verifying session credentials</p>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

