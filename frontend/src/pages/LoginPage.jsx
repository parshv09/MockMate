import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AlertCircle, Eye, EyeOff, Loader2, LogIn } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { extractApiError } from "../utils/apiErrors.js";
import { Button } from "../components/ui/Button.jsx";
import { FormField } from "../components/ui/FormField.jsx";

export function LoginPage() {
  const { login } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectTo = location.state?.from?.pathname || "/dashboard";

  function validateForm() {
    const errors = {};
    if (!username.trim()) {
      errors.username = "Please enter your username or email.";
    }
    if (!password) {
      errors.password = "Please enter your password.";
    }
    return errors;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    const clientErrors = validateForm();
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      return;
    }

    setFieldErrors({});
    setIsSubmitting(true);

    try {
      const data = await login({
        username: username.trim(),
        password,
      });

      const displayName = data?.user?.first_name || data?.user?.username || "back";
      showToast({
        title: `Welcome ${displayName === "back" ? "back" : `back, ${displayName}`}`,
        description: "Your interview studio is ready.",
        tone: "success",
      });

      navigate(redirectTo, { replace: true });
    } catch (error) {
      const parsed = extractApiError(error, "Unable to sign in. Please check your credentials.");
      setFieldErrors(parsed.fieldErrors);
      setFormError(parsed.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6 rounded-2xl border border-white/15 bg-white p-6 text-foreground shadow-2xl sm:p-8">
      <div className="space-y-1.5">
        <span className="inline-flex items-center rounded-full bg-primary-subtle px-3 py-1 text-xs font-semibold text-primary">
          Candidate Studio
        </span>
        <h1 className="pt-1 font-display text-2xl font-bold tracking-tight text-foreground">
          Sign in to MockMate
        </h1>
        <p className="text-sm text-foreground-secondary">
          Enter your username or email to continue practicing.
        </p>
      </div>

      {formError ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-destructive/25 bg-destructive-bg p-3.5 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{formError}</span>
        </div>
      ) : null}

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <FormField
          label="Username or Email"
          name="username"
          type="text"
          value={username}
          onChange={(e) => {
            setUsername(e.target.value);
            if (fieldErrors.username) {
              setFieldErrors((prev) => ({ ...prev, username: "" }));
            }
          }}
          placeholder="alex.chen or alex@example.com"
          autoComplete="username"
          required
          disabled={isSubmitting}
          error={fieldErrors.username}
        />

        <FormField
          label="Password"
          name="password"
          type={showPassword ? "text" : "password"}
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (fieldErrors.password) {
              setFieldErrors((prev) => ({ ...prev, password: "" }));
            }
          }}
          placeholder="Enter your password"
          autoComplete="current-password"
          required
          disabled={isSubmitting}
          error={fieldErrors.password}
          rightElement={
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="rounded p-1 text-foreground-muted transition-colors hover:text-foreground"
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Eye className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          }
        />

        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isSubmitting}
          className="w-full shadow-md"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              <span>Signing in...</span>
            </>
          ) : (
            <>
              <LogIn className="h-4 w-4" aria-hidden="true" />
              <span>Sign in</span>
            </>
          )}
        </Button>
      </form>

      <div className="border-t border-border pt-4 text-center text-sm text-foreground-secondary">
        New to MockMate?{" "}
        <Link to="/register" className="font-semibold text-primary hover:underline">
          Create an account
        </Link>
      </div>
    </div>
  );
}
