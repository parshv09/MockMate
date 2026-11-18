import { useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, Loader2, PlayCircle, Upload } from "lucide-react";
import { Button } from "../ui/Button.jsx";
import { ResumeSelector } from "../resumes/ResumeSelector.jsx";

const DIFFICULTY_OPTIONS = [
  { value: 1, label: "1 — Foundational" },
  { value: 2, label: "2 — Entry Level" },
  { value: 3, label: "3 — Intermediate" },
  { value: 4, label: "4 — Advanced" },
  { value: 5, label: "5 — Expert" },
];

export function ResumeJDInterviewForm({
  resumes = [],
  resumesLoading = false,
  resumesError = "",
  onRetryResumes,
  isSubmitting = false,
  formError = "",
  fieldErrors = {},
  onSubmit,
}) {
  const [selectedResumeId, setSelectedResumeId] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [difficulty, setDifficulty] = useState(3);
  const [nQuestions, setNQuestions] = useState(5);
  const [localError, setLocalError] = useState("");
  const [localFieldErrors, setLocalFieldErrors] = useState({});

  const mergedFieldErrors = { ...localFieldErrors, ...fieldErrors };
  const combinedError = localError || formError;

  function handleSelectResume(chosen) {
    if (!chosen) return;
    setLocalError("");
    setSelectedResumeId((prev) => (prev === chosen.id ? null : chosen.id));
  }

  function validate() {
    const errors = {};
    const hasResume = selectedResumeId !== null;
    const hasJd = jobDescription.trim().length > 0;

    if (!hasResume && !hasJd) {
      setLocalError(
        "Please select a saved resume or paste a job description to tailor your interview."
      );
      return false;
    }

    const diffNum = Number(difficulty);
    if (!Number.isInteger(diffNum) || diffNum < 1 || diffNum > 5) {
      errors.difficulty = "Difficulty must be between 1 and 5.";
    }

    const countNum = Number(nQuestions);
    if (!Number.isInteger(countNum) || countNum < 1 || countNum > 30) {
      errors.n_questions = "Number of questions must be between 1 and 30.";
    }

    if (Object.keys(errors).length > 0) {
      setLocalFieldErrors(errors);
      return false;
    }

    return true;
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;

    setLocalError("");
    setLocalFieldErrors({});

    if (!validate()) {
      return;
    }

    onSubmit?.({
      resume_id: selectedResumeId,
      job_description: jobDescription.trim(),
      difficulty: Number(difficulty),
      n_questions: Number(nQuestions),
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {combinedError ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-destructive/25 bg-destructive-bg p-3.5 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{combinedError}</span>
        </div>
      ) : null}

      {/* Step 1: Select Saved Resume */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              1. Select a resume from your Resume Vault
            </h3>
            <p className="text-xs text-slate-500">
              Click a resume to select it, or click again to deselect.
            </p>
          </div>
          <Link
            to="/resumes"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
          >
            <Upload className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Manage resumes</span>
          </Link>
        </div>

        <ResumeSelector
          resumes={resumes}
          selectedResumeId={selectedResumeId}
          onSelect={handleSelectResume}
          isLoading={resumesLoading}
          error={resumesError}
          onRetry={onRetryResumes}
        />
      </div>

      {/* Step 2: Job Description */}
      <div className="space-y-1.5">
        <label
          htmlFor="resume-jd-textarea"
          className="block text-sm font-semibold text-slate-900"
        >
          2. Job description
        </label>
        <p className="text-xs text-slate-500">
          Paste the target job posting so questions focus on the skills and responsibilities the role requires.
        </p>
        <textarea
          id="resume-jd-textarea"
          name="job_description"
          rows={6}
          value={jobDescription}
          onChange={(e) => {
            setJobDescription(e.target.value);
            if (localError) setLocalError("");
          }}
          disabled={isSubmitting}
          placeholder="Paste the role summary, required skills, and key responsibilities..."
          className="mt-1.5 block w-full rounded-lg border border-border-strong bg-surface px-3.5 py-2.5 text-sm leading-relaxed text-foreground placeholder:text-foreground-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60"
        />
        {mergedFieldErrors.job_description ? (
          <p role="alert" className="text-xs font-medium text-destructive">
            {mergedFieldErrors.job_description}
          </p>
        ) : null}
      </div>

      {/* Step 3: Difficulty & Question Count */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label
            htmlFor="resume-jd-difficulty"
            className="block text-sm font-medium text-foreground"
          >
            Difficulty level
          </label>
          <select
            id="resume-jd-difficulty"
            name="difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(Number(e.target.value))}
            disabled={isSubmitting}
            className="block w-full rounded-md border border-border-strong bg-surface px-3.5 py-2.5 text-sm text-foreground transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60"
          >
            {DIFFICULTY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {mergedFieldErrors.difficulty ? (
            <p role="alert" className="text-xs font-medium text-destructive">
              {mergedFieldErrors.difficulty}
            </p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <label
            htmlFor="resume-jd-n-questions"
            className="block text-sm font-medium text-foreground"
          >
            Number of questions
          </label>
          <input
            id="resume-jd-n-questions"
            name="n_questions"
            type="number"
            min={1}
            max={30}
            value={nQuestions}
            onChange={(e) => {
              setNQuestions(e.target.value);
              if (localFieldErrors.n_questions) {
                setLocalFieldErrors((prev) => ({ ...prev, n_questions: "" }));
              }
            }}
            disabled={isSubmitting}
            className="block w-full rounded-md border border-border-strong bg-surface px-3.5 py-2.5 text-sm text-foreground transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-subtle disabled:opacity-60"
          />
          <p className="text-xs text-foreground-muted">Choose between 1 and 30 questions.</p>
          {mergedFieldErrors.n_questions ? (
            <p role="alert" className="text-xs font-medium text-destructive">
              {mergedFieldErrors.n_questions}
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
              <span>Start Tailored Interview</span>
            </>
          )}
        </Button>
      </div>
    </form>
  );
}

