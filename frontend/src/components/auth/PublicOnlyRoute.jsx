import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";

export function PublicOnlyRoute() {
  const { isAuthenticated, isInitializing } = useAuth();
  const location = useLocation();

  if (isInitializing) {
    return (
      <div
        role="status"
        aria-label="Checking session"
        className="flex items-center justify-center py-12"
      >
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (isAuthenticated) {
    const redirectTo = location.state?.from?.pathname || "/dashboard";
    return <Navigate to={redirectTo} replace />;
  }

  return <Outlet />;
}

