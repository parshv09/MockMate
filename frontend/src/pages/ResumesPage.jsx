import { useCallback, useEffect, useState } from "react";
import { AlertCircle, FileText, Plus, RefreshCw } from "lucide-react";
import { deleteResume, fetchResumes } from "../api/resumes.api.js";
import { useToast } from "../context/ToastContext.jsx";
import { extractApiError } from "../utils/apiErrors.js";
import { validateResumeFileClient } from "../utils/resumeValidation.js";
import { Button } from "../components/ui/Button.jsx";
import { ConfirmDialog } from "../components/ui/ConfirmDialog.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";
import { FileDropzone } from "../components/resumes/FileDropzone.jsx";
import { ResumeCard } from "../components/resumes/ResumeCard.jsx";
import { ResumeUploadModal } from "../components/resumes/ResumeUploadModal.jsx";

function ResumesSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-label="Loading resumes">
      <div className="rounded-2xl bg-[#0B1528] p-6 sm:p-8">
        <div className="h-7 w-48 rounded bg-white/10" />
        <div className="mt-2 h-4 w-72 max-w-full rounded bg-white/10" />
      </div>

      <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
        <div className="h-32 rounded-xl bg-slate-100" />
      </div>

      <div className="space-y-3">
        {[1, 2, 3].map((item) => (
          <div
            key={item}
            className="h-20 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm"
          >
            <div className="h-4 w-48 rounded bg-slate-200" />
            <div className="mt-2 h-3 w-64 rounded bg-slate-100" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function ResumesPage() {
  const { showToast } = useToast();

  const [resumes, setResumes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const [dropzoneError, setDropzoneError] = useState("");
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [queuedFile, setQueuedFile] = useState(null);

  const [resumeToDelete, setResumeToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadResumes = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const list = await fetchResumes();
      setResumes(list);
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Unable to load your saved resumes right now."
      );
      setErrorMessage(parsed.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadResumes();
  }, [loadResumes]);

  function handleOpenUploadModal(file = null) {
    setDropzoneError("");
    setQueuedFile(file);
    setIsUploadModalOpen(true);
  }

  function handleDropzoneSelect(file) {
    const validation = validateResumeFileClient(file);
    if (!validation.valid) {
      setDropzoneError(validation.error);
      return;
    }
    handleOpenUploadModal(file);
  }

  async function handleUploadSuccess(createdResume) {
    setIsUploadModalOpen(false);
    setQueuedFile(null);
    await loadResumes();
    showToast({
      title: "Resume uploaded",
      description: `${createdResume?.title || createdResume?.file_name || "Your resume"} has been saved.`,
      tone: "success",
    });
  }

  async function handleConfirmDelete() {
    if (!resumeToDelete || isDeleting) return;

    setIsDeleting(true);
    const target = resumeToDelete;

    try {
      await deleteResume(target.id);
      setResumes((prev) => prev.filter((item) => item.id !== target.id));
      setResumeToDelete(null);
      showToast({
        title: "Resume deleted",
        description: `${target.title || target.file_name || "Resume"} was removed from your vault.`,
        tone: "info",
      });
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Could not delete this resume. Please try again."
      );
      showToast({
        title: "Delete failed",
        description: parsed.message,
        tone: "error",
      });
    } finally {
      setIsDeleting(false);
    }
  }

  if (isLoading) {
    return <ResumesSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Studio Header Banner */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#070D19] via-[#0B1528] to-[#0F1D3A] p-6 text-white shadow-lg sm:p-8">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-primary/25 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-20 left-1/3 h-56 w-56 rounded-full bg-secondary/20 blur-3xl"
        />

        <div className="relative flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-teal-300">
              <FileText className="h-3.5 w-3.5" aria-hidden="true" />
              Resume Vault
            </span>
            <h1 className="font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Your Resumes
            </h1>
            <p className="max-w-xl text-sm text-slate-300">
              Upload and manage your resumes to tailor mock interview questions to your background.
            </p>
          </div>

          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={() => handleOpenUploadModal(null)}
            className="w-full shrink-0 shadow-md sm:w-auto"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            <span>Upload Resume</span>
          </Button>
        </div>
      </section>

      {/* Error State with Retry */}
      {errorMessage ? (
        <div
          role="alert"
          className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-destructive/30 bg-destructive-bg p-5 sm:flex-row sm:items-center"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden="true" />
            <div>
              <h2 className="text-sm font-semibold text-destructive">
                Could not load resumes
              </h2>
              <p className="mt-0.5 text-sm text-foreground-secondary">{errorMessage}</p>
            </div>
          </div>

          <Button variant="secondary" size="sm" onClick={loadResumes}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Retry</span>
          </Button>
        </div>
      ) : null}

      {/* Drag-and-Drop Quick Upload Area */}
      <section
        aria-label="Quick resume upload"
        className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6"
      >
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="font-display text-base font-bold text-slate-900">
              Quick Upload
            </h2>
            <p className="text-xs text-slate-500">
              Drop a PDF, TXT, or MD file here (up to 10 MB) to add it to your vault.
            </p>
          </div>
        </div>

        <FileDropzone
          onFileSelect={handleDropzoneSelect}
          error={dropzoneError}
        />
      </section>

      {/* Saved Resumes Listing */}
      <section aria-label="Saved resumes" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-base font-bold text-slate-900">
            Saved Resumes ({resumes.length})
          </h2>
        </div>

        {resumes.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No resumes in your vault yet"
            description="Upload your resume in PDF, TXT, or MD format to prepare for tailored mock interviews."
            action={
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => handleOpenUploadModal(null)}
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                <span>Upload Your First Resume</span>
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {resumes.map((resume) => (
              <ResumeCard
                key={resume.id}
                resume={resume}
                onDelete={(target) => setResumeToDelete(target)}
                isDeleting={isDeleting && resumeToDelete?.id === resume.id}
              />
            ))}
          </div>
        )}
      </section>

      {/* Upload Modal */}
      <ResumeUploadModal
        isOpen={isUploadModalOpen}
        initialFile={queuedFile}
        onClose={() => {
          setIsUploadModalOpen(false);
          setQueuedFile(null);
        }}
        onSuccess={handleUploadSuccess}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={Boolean(resumeToDelete)}
        title="Delete resume?"
        description={`Are you sure you want to delete "${
          resumeToDelete?.title || resumeToDelete?.file_name || "this resume"
        }"? This action cannot be undone.`}
        confirmLabel="Delete Resume"
        cancelLabel="Cancel"
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!isDeleting) setResumeToDelete(null);
        }}
      />
    </div>
  );
}
