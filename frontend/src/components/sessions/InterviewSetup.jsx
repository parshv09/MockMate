import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Briefcase, FileText, Sparkles } from "lucide-react";
import { useAuth } from "../../context/AuthContext.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import { fetchResumes } from "../../api/resumes.api.js";
import {
  createAdaptiveSession,
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

  async function handleAdaptiveSubmit(payload) {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setFormError("");
    setFieldErrors({});

    try {
      const data = await createAdaptiveSession(payload);
      const sessionId = data?.session?.id;
      if (!sessionId) {
        throw new Error("Session was created without a valid session ID.");
      }

      showToast({
        title: "Adaptive interview ready",
        description: "Your adaptive practice session has been created.",
        tone: "success",
      });

      navigate(`/sessions/${sessionId}/interview`);
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Unable to start the adaptive interview. Please try again."
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
      <section aria-label="Interview mode selection" className="grid grid-cols-1 gap-4 md:grid-cols-3">
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
          description="Practice adaptive questions grounded in your uploaded resume and target job description, with dynamic follow-ups."
          selected={mode === "resume_jd"}
          disabled={isSubmitting}
          onSelect={() => handleModeChange("resume_jd")}
        />

        <InterviewModeCard
          icon={Sparkles}
          title="Adaptive Interview"
          badgeText="Dynamic"
          description="Questions adapt in difficulty based on your responses, with targeted follow-ups when deeper clarification is needed."
          selected={mode === "adaptive"}
          disabled={isSubmitting}
          onSelect={() => handleModeChange("adaptive")}
        />
      </section>

      {/* Active Mode Configuration Form */}
      <section
        aria-label={
          mode === "standard"
            ? "Standard interview configuration"
            : mode === "adaptive"
            ? "Adaptive interview configuration"
            : "Resume and job description interview configuration"
        }
        className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-8"
      >
        <div className="mb-6 border-b border-slate-200/80 pb-4">
          <h2 className="font-display text-lg font-bold text-slate-900">
            {mode === "standard"
              ? "Configure Standard Interview"
              : mode === "adaptive"
              ? "Configure Adaptive Interview"
              : "Configure Resume + Job Description Interview"}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {mode === "standard"
              ? "Choose your interview focus, target role, difficulty, and question count."
              : mode === "adaptive"
              ? "Set your focus, target role, starting difficulty, and main question budget."
              : "Select a saved resume, paste the job description, and set your starting difficulty and main question budget."}
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
        ) : mode === "adaptive" ? (
          <StandardInterviewForm
            defaultJobRole={user?.target_role || "Software Engineer"}
            isSubmitting={isSubmitting}
            formError={formError}
            fieldErrors={fieldErrors}
            onSubmit={handleAdaptiveSubmit}
            submitLabel="Start Adaptive Interview"
            questionCountLabel="Number of main questions"
            questionCountHint="Choose 1 to 30 main questions. Follow-ups may be asked dynamically."
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

