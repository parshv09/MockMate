import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import { ToastProvider } from "./context/ToastContext.jsx";
import { ProtectedRoute } from "./components/auth/ProtectedRoute.jsx";
import { PublicOnlyRoute } from "./components/auth/PublicOnlyRoute.jsx";
import { AppShell } from "./components/layout/AppShell.jsx";
import { AuthLayout } from "./components/layout/AuthLayout.jsx";
import { InterviewBoothLayout } from "./components/layout/InterviewBoothLayout.jsx";
import { LandingPage } from "./pages/LandingPage.jsx";
import { LoginPage } from "./pages/LoginPage.jsx";
import { RegisterPage } from "./pages/RegisterPage.jsx";
import { DashboardPage } from "./pages/DashboardPage.jsx";
import { InterviewHistoryPage } from "./pages/InterviewHistoryPage.jsx";
import { ResumesPage } from "./pages/ResumesPage.jsx";
import { SessionSetupPage } from "./pages/SessionSetupPage.jsx";
import { InterviewWorkspacePage } from "./pages/InterviewWorkspacePage.jsx";
import { SessionSummaryPage } from "./pages/SessionSummaryPage.jsx";
import { NotFoundPage } from "./pages/NotFoundPage.jsx";

export function AppRoutes() {
  return (
    <Routes>
      {/* Public Landing Route */}
      <Route path="/" element={<LandingPage />} />

      {/* Public-Only Authentication Routes */}
      <Route element={<PublicOnlyRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
      </Route>

      {/* Protected Studio & Interview Routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/history" element={<InterviewHistoryPage />} />
          <Route path="/resumes" element={<ResumesPage />} />
          <Route path="/sessions/new" element={<SessionSetupPage />} />
          <Route path="/sessions/:id/summary" element={<SessionSummaryPage />} />
        </Route>

        <Route element={<InterviewBoothLayout />}>
          <Route path="/sessions/:id/interview" element={<InterviewWorkspacePage />} />
        </Route>
      </Route>

      {/* Fallback 404 Route */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
