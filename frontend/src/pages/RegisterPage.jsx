import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, Check, Eye, EyeOff, Loader2, UserPlus } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { extractApiError } from "../utils/apiErrors.js";
import { Button } from "../components/ui/Button.jsx";
import { FormField } from "../components/ui/FormField.jsx";

const INITIAL_FORM = {
  first_name: "",
  last_name: "",
  username: "",
  email: "",
  user_type: "student",
  target_role: "",
  password: "",
  confirm_password: "",
};

export function RegisterPage() {
  const { register } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [form, setForm] = useState(INITIAL_FORM);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateField(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: "" }));
    }
  }

  function validateForm() {
    const errors = {};
    if (!form.first_name.trim()) {
      errors.first_name = "First name is required.";
    }
    if (!form.last_name.trim()) {
      errors.last_name = "Last name is required.";
    }
    if (!form.username.trim()) {
      errors.username = "Username is required.";
    } else if (form.username.trim().length < 3) {
      errors.username = "Username must be at least 3 characters.";
    }

    if (!form.email.trim()) {
      errors.email = "Email address is required.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      errors.email = "Please enter a valid email address.";
    }

    if (!form.password) {
      errors.password = "Password is required.";
    } else if (form.password.length < 8) {
      errors.password = "Password must be at least 8 characters.";
    } else if (!/[A-Z]/.test(form.password)) {
      errors.password = "Password must contain at least one uppercase letter.";
    } else if (!/[a-z]/.test(form.password)) {
      errors.password = "Password must contain at least one lowercase letter.";
    } else if (!/[0-9]/.test(form.password)) {
      errors.password = "Password must contain at least one number.";
    }

    if (!form.confirm_password) {
      errors.confirm_password = "Please confirm your password.";
    } else if (form.password !== form.confirm_password) {
      errors.confirm_password = "Passwords do not match.";
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
      const payload = {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        username: form.username.trim(),
        email: form.email.trim(),
        user_type: form.user_type,
        target_role: form.target_role.trim(),
        password: form.password,
        confirm_password: form.confirm_password,
      };

      const data = await register(payload);
      const displayName = data?.user?.first_name || data?.user?.username || "there";

      showToast({
        title: `Welcome to MockMate, ${displayName}`,
        description: "Your account has been created.",
        tone: "success",
      });

      navigate("/dashboard", { replace: true });
    } catch (error) {
      const parsed = extractApiError(error, "Registration failed. Please review the form.");
      setFieldErrors(parsed.fieldErrors);
      setFormError(parsed.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const passwordRules = [
    { label: "8+ characters", met: form.password.length >= 8 },
    { label: "Uppercase letter", met: /[A-Z]/.test(form.password) },
    { label: "Lowercase letter", met: /[a-z]/.test(form.password) },
    { label: "Number", met: /[0-9]/.test(form.password) },
  ];

  return (
    <div className="space-y-6 rounded-2xl border border-white/15 bg-white p-6 text-foreground shadow-2xl sm:p-8">
      <div className="space-y-1.5">
        <span className="inline-flex items-center rounded-full bg-secondary-subtle px-3 py-1 text-xs font-semibold text-secondary">
          Get Started Free
        </span>
        <h1 className="pt-1 font-display text-2xl font-bold tracking-tight text-foreground">
          Create your MockMate account
        </h1>
        <p className="text-sm text-foreground-secondary">
          Set up your profile to start practicing role-specific and resume-based interviews.
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
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            label="First name"
            name="first_name"
            value={form.first_name}
            onChange={(e) => updateField("first_name", e.target.value)}
            placeholder="Alex"
            autoComplete="given-name"
            required
            disabled={isSubmitting}
            error={fieldErrors.first_name}
          />

          <FormField
            label="Last name"
            name="last_name"
            value={form.last_name}
            onChange={(e) => updateField("last_name", e.target.value)}
            placeholder="Chen"
            autoComplete="family-name"
            required
            disabled={isSubmitting}
            error={fieldErrors.last_name}
          />
        </div>

        <FormField
          label="Username"
          name="username"
          value={form.username}
          onChange={(e) => updateField("username", e.target.value)}
          placeholder="alexchen"
          autoComplete="username"
          hint="At least 3 characters."
          required
          disabled={isSubmitting}
          error={fieldErrors.username}
        />

        <FormField
          label="Email"
          name="email"
          type="email"
          value={form.email}
          onChange={(e) => updateField("email", e.target.value)}
          placeholder="alex@example.com"
          autoComplete="email"
          required
          disabled={isSubmitting}
          error={fieldErrors.email}
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label htmlFor="field-user_type" className="block text-sm font-medium text-foreground">
              Profile type
            </label>
            <select
              id="field-user_type"
              name="user_type"
              value={form.user_type}
              onChange={(e) => updateField("user_type", e.target.value)}
              disabled={isSubmitting}
              className="block w-full rounded-md border border-border-strong bg-surface px-3.5 py-2.5 text-sm text-foreground transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60"
            >
              <option value="student">Student</option>
              <option value="job_seeker">Job Seeker</option>
            </select>
            {fieldErrors.user_type ? (
              <p role="alert" className="text-xs font-medium text-destructive">
                {fieldErrors.user_type}
              </p>
            ) : null}
          </div>

          <FormField
            label="Target role"
            name="target_role"
            value={form.target_role}
            onChange={(e) => updateField("target_role", e.target.value)}
            placeholder="e.g. Software Engineer"
            disabled={isSubmitting}
            error={fieldErrors.target_role}
          />
        </div>

        <div className="space-y-2">
          <FormField
            label="Password"
            name="password"
            type={showPassword ? "text" : "password"}
            value={form.password}
            onChange={(e) => updateField("password", e.target.value)}
            placeholder="Create a strong password"
            autoComplete="new-password"
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

          <ul className="grid grid-cols-2 gap-1.5 text-xs" aria-label="Password requirements">
            {passwordRules.map((rule) => (
              <li
                key={rule.label}
                className={`flex items-center gap-1.5 ${
                  rule.met ? "text-success" : "text-foreground-muted"
                }`}
              >
                <Check className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span>{rule.label}</span>
              </li>
            ))}
          </ul>
        </div>

        <FormField
          label="Confirm password"
          name="confirm_password"
          type={showConfirmPassword ? "text" : "password"}
          value={form.confirm_password}
          onChange={(e) => updateField("confirm_password", e.target.value)}
          placeholder="Re-enter your password"
          autoComplete="new-password"
          required
          disabled={isSubmitting}
          error={fieldErrors.confirm_password}
          rightElement={
            <button
              type="button"
              onClick={() => setShowConfirmPassword((prev) => !prev)}
              aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
              className="rounded p-1 text-foreground-muted transition-colors hover:text-foreground"
            >
              {showConfirmPassword ? (
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
              <span>Creating account...</span>
            </>
          ) : (
            <>
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              <span>Create account</span>
            </>
          )}
        </Button>
      </form>

      <div className="border-t border-border pt-4 text-center text-sm text-foreground-secondary">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-primary hover:underline">
          Sign in
        </Link>
      </div>
    </div>
  );
}
