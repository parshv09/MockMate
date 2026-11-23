import { useState } from "react";
import { AlertCircle, Loader2, PlayCircle } from "lucide-react";
import { Button } from "../ui/Button.jsx";
import { FormField } from "../ui/FormField.jsx";

const ROLE_OPTIONS = [
  { value: "tech", label: "Technical" },
  { value: "hr", label: "Human Resources (HR)" },
  { value: "apt", label: "Aptitude" },
  { value: "beh", label: "Behavioral" },
];

const DIFFICULTY_OPTIONS = [
  { value: 1, label: "1 — Foundational" },
  { value: 2, label: "2 — Entry Level" },
  { value: 3, label: "3 — Intermediate" },
  { value: 4, label: "4 — Advanced" },
  { value: 5, label: "5 — Expert" },
];

export function StandardInterviewForm({
  defaultJobRole = "Software Engineer",
  isSubmitting = false,
  formError = "",
  fieldErrors = {},
  onSubmit,
}) {
  const [role, setRole] = useState("tech");
  const [jobRole, setJobRole] = useState(defaultJobRole || "Software Engineer");
  const [difficulty, setDifficulty] = useState(3);
  const [nQuestions, setNQuestions] = useState(5);
  const [localErrors, setLocalErrors] = useState({});

  const mergedErrors = { ...localErrors, ...fieldErrors };
  const isHrRole = role === "hr";

  function validate() {
    const errors = {};
    if (jobRole.trim().length > 100) {
      errors.job_role = "Job role must be 100 characters or fewer.";
    }
    const diffNum = isHrRole ? 3 : Number(difficulty);
    if (!Number.isInteger(diffNum) || diffNum < 1 || diffNum > 5) {
      errors.difficulty = "Difficulty must be between 1 and 5.";
    }
    const countNum = Number(nQuestions);
    if (!Number.isInteger(countNum) || countNum < 1 || countNum > 30) {
      errors.n_questions = "Number of questions must be between 1 and 30.";
    }
    return errors;
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;

    const errors = validate();
    if (Object.keys(errors).length > 0) {
      setLocalErrors(errors);
      return;
    }

    setLocalErrors({});
    onSubmit?.({
      role,
      job_role: jobRole.trim() || "Software Engineer",
      difficulty: isHrRole ? 3 : Number(difficulty),
      n_questions: Number(nQuestions),
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {formError ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-destructive/25 bg-destructive-bg p-3.5 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{formError}</span>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label
            htmlFor="standard-role"
            className="block text-sm font-medium text-foreground"
          >
            Interview focus
          </label>
          <select
            id="standard-role"
            name="role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            disabled={isSubmitting}
            className="block w-full rounded-md border border-border-strong bg-surface px-3.5 py-2.5 text-sm text-foreground transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60"
          >
            {ROLE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {mergedErrors.role ? (
            <p role="alert" className="text-xs font-medium text-destructive">
              {mergedErrors.role}
            </p>
          ) : null}
        </div>

        <FormField
          label="Target job role"
          name="job_role"
          value={jobRole}
          onChange={(e) => {
            setJobRole(e.target.value);
            if (localErrors.job_role) {
              setLocalErrors((prev) => ({ ...prev, job_role: "" }));
            }
          }}
          placeholder="e.g. Software Engineer"
          hint="Defaults to Software Engineer if left blank."
          disabled={isSubmitting}
          error={mergedErrors.job_role}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label
            htmlFor="standard-difficulty"
            className="block text-sm font-medium text-foreground"
          >
            Difficulty level
          </label>
          <select
            id="standard-difficulty"
            name="difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(Number(e.target.value))}
            disabled={isSubmitting || isHrRole}
            className="block w-full rounded-md border border-border-strong bg-surface px-3.5 py-2.5 text-sm text-foreground transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60"
          >
            {DIFFICULTY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {isHrRole ? (
            <p className="text-xs text-foreground-muted">
              Standard HR questions are not filtered by difficulty level.
            </p>
          ) : null}
          {mergedErrors.difficulty ? (
            <p role="alert" className="text-xs font-medium text-destructive">
              {mergedErrors.difficulty}
            </p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <label
            htmlFor="standard-n-questions"
            className="block text-sm font-medium text-foreground"
          >
            Number of questions
          </label>
          <input
            id="standard-n-questions"
            name="n_questions"
            type="number"
            min={1}
            max={30}
            value={nQuestions}
            onChange={(e) => {
              setNQuestions(e.target.value);
              if (localErrors.n_questions) {
                setLocalErrors((prev) => ({ ...prev, n_questions: "" }));
              }
            }}
            disabled={isSubmitting}
            className="block w-full rounded-md border border-border-strong bg-surface px-3.5 py-2.5 text-sm text-foreground transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60"
          />
          <p className="text-xs text-foreground-muted">Choose between 1 and 30 questions.</p>
          {mergedErrors.n_questions ? (
            <p role="alert" className="text-xs font-medium text-destructive">
              {mergedErrors.n_questions}
            </p>
          ) : null}
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isSubmitting}
          disabled={isSubmitting}
          className="w-full shadow-md sm:w-auto"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              <span>Preparing your interview...</span>
            </>
          ) : (
            <>
              <PlayCircle className="h-4 w-4" aria-hidden="true" />
              <span>Start Standard Interview</span>
            </>
          )}
        </Button>
      </div>
    </form>
  );
}

