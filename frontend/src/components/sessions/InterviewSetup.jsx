import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Briefcase, FileText } from "lucide-react";
import { useAuth } from "../../context/AuthContext.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import { fetchResumes } from "../../api/resumes.api.js";
import {
  createResumeJdSession,
  createStandardSession,
} from "../../api/sessions.api.js";
import { extractApiError } from "../../utils/apiErrors.js";
import { InterviewModeCard } from "./InterviewModeCard.jsx";
import { StandardInterviewForm } from "./StandardInterviewForm.jsx";
import { ResumeJDInterviewForm } from "./ResumeJDInterviewForm.jsx";

export function InterviewSetup() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [mode, setMode] = useState("standard");
  const [resumes, setResumes] = useState([]);
  const [resumesLoading, setResumesLoading] = useState(true);
  const [resumesError, setResumesError] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});

  const loadResumes = useCallback(async () => {
    setResumesLoading(true);
    setResumesError("");
    try {
      const list = await fetchResumes();
      setResumes(list);
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Could not load your saved resumes."
      );
      setResumesError(parsed.message);
    } finally {
      setResumesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadResumes();
  }, [loadResumes]);

  function handleModeChange(nextMode) {
    if (isSubmitting) return;
    setMode(nextMode);
    setFormError("");
    setFieldErrors({});
  }

  async function handleStandardSubmit(payload) {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setFormError("");
    setFieldErrors({});

    try {
      const data = await createStandardSession(payload);
      const sessionId = data?.session?.id;
      if (!sessionId) {
        throw new Error("Session was created without a valid session ID.");
      }

      showToast({
        title: "Interview ready",
        description: "Your practice session has been created.",
        tone: "success",
      });

      navigate(`/sessions/${sessionId}/interview`);
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Unable to start the interview session. Please try again."
      );
      setFieldErrors(parsed.fieldErrors);
      setFormError(parsed.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleResumeJdSubmit(payload) {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setFormError("");
    setFieldErrors({});

    try {
      const data = await createResumeJdSession(payload);
      const sessionId = data?.session?.id;
      if (!sessionId) {
        throw new Error("Session was created without a valid session ID.");
      }

      showToast({
        title: "Tailored interview ready",
        description: "Your personalized practice session has been created.",
        tone: "success",
      });

      navigate(`/sessions/${sessionId}/interview`);
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Unable to start the tailored interview. Please try again."
      );
      setFieldErrors(parsed.fieldErrors);
      setFormError(parsed.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Mode Selection Cards */}
      <section aria-label="Interview mode selection" className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <InterviewModeCard
          icon={Briefcase}
          title="Standard Interview"
          badgeText="Quick Start"
          description="Practice technical, HR, aptitude, or behavioral questions tailored to your target job role and difficulty level."
          selected={mode === "standard"}
          disabled={isSubmitting}
          onSelect={() => handleModeChange("standard")}
        />

        <InterviewModeCard
          icon={FileText}
          title="Resume + Job Description"
          badgeText="Personalized"
          description="Practice questions tailored to your uploaded resume and the exact job description you are applying for."
          selected={mode === "resume_jd"}
          disabled={isSubmitting}
          onSelect={() => handleModeChange("resume_jd")}
        />
      </section>

      {/* Active Mode Configuration Form */}
      <section
        aria-label={
          mode === "standard"
            ? "Standard interview configuration"
            : "Resume and job description interview configuration"
        }
        className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-8"
      >
        <div className="mb-6 border-b border-slate-200/80 pb-4">
          <h2 className="font-display text-lg font-bold text-slate-900">
            {mode === "standard"
              ? "Configure Standard Interview"
              : "Configure Resume + Job Description Interview"}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {mode === "standard"
              ? "Choose your interview focus, target role, difficulty, and question count."
              : "Select a saved resume, paste the job description, and set your session preferences."}
          </p>
        </div>

        {mode === "standard" ? (
          <StandardInterviewForm
            defaultJobRole={user?.target_role || "Software Engineer"}
            isSubmitting={isSubmitting}
            formError={formError}
            fieldErrors={fieldErrors}
            onSubmit={handleStandardSubmit}
          />
        ) : (
          <ResumeJDInterviewForm
            resumes={resumes}
            resumesLoading={resumesLoading}
            resumesError={resumesError}
            onRetryResumes={loadResumes}
            isSubmitting={isSubmitting}
            formError={formError}
            fieldErrors={fieldErrors}
            onSubmit={handleResumeJdSubmit}
          />
        )}
      </section>
    </div>
  );
}

