import { useEffect, useState } from "react";
import { AlertCircle, Loader2, Upload, X } from "lucide-react";
import { uploadResume } from "../../api/resumes.api.js";
import { extractApiError } from "../../utils/apiErrors.js";
import {
  MAX_RESUME_TITLE_LENGTH,
  validateResumeFileClient,
} from "../../utils/resumeValidation.js";
import { Button } from "../ui/Button.jsx";
import { FormField } from "../ui/FormField.jsx";
import { FileDropzone } from "./FileDropzone.jsx";

export function ResumeUploadModal({
  isOpen,
  initialFile = null,
  onClose,
  onSuccess,
}) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(initialFile);
  const [fileError, setFileError] = useState("");
  const [titleError, setTitleError] = useState("");
  const [formError, setFormError] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setTitle("");
      setFileError("");
      setTitleError("");
      setFormError("");
      setUploadProgress(0);
      setIsUploading(false);

      if (initialFile) {
        const validation = validateResumeFileClient(initialFile);
        if (validation.valid) {
          setFile(initialFile);
        } else {
          setFile(null);
          setFileError(validation.error);
        }
      } else {
        setFile(null);
      }
    }
  }, [isOpen, initialFile]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !isUploading) {
        onClose?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isUploading, onClose]);

  if (!isOpen) return null;

  function handleFileSelect(selectedFile) {
    setFormError("");
    const validation = validateResumeFileClient(selectedFile);
    if (!validation.valid) {
      setFile(null);
      setFileError(validation.error);
      return;
    }
    setFile(selectedFile);
    setFileError("");
  }

  function handleClearFile() {
    setFile(null);
    setFileError("");
    setFormError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (isUploading) return;

    setFormError("");
    setTitleError("");

    const trimmedTitle = title.trim();
    if (trimmedTitle.length > MAX_RESUME_TITLE_LENGTH) {
      setTitleError(`Title must be ${MAX_RESUME_TITLE_LENGTH} characters or fewer.`);
      return;
    }

    const validation = validateResumeFileClient(file);
    if (!validation.valid) {
      setFileError(validation.error);
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const createdResume = await uploadResume({
        title: trimmedTitle,
        file,
        onUploadProgress: (progressEvent) => {
          if (progressEvent?.total) {
            const percent = Math.min(
              100,
              Math.round((progressEvent.loaded * 100) / progressEvent.total)
            );
            setUploadProgress(percent);
          }
        },
      });

      await onSuccess?.(createdResume);
    } catch (error) {
      const parsed = extractApiError(
        error,
        "Could not upload resume. Please check your file and try again."
      );
      if (parsed.fieldErrors.file) {
        setFileError(parsed.fieldErrors.file);
      }
      if (parsed.fieldErrors.title) {
        setTitleError(parsed.fieldErrors.title);
      }
      setFormError(parsed.message);
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#070D19]/70 p-4 backdrop-blur-xs"
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-resume-modal-title"
        className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2
              id="upload-resume-modal-title"
              className="font-display text-lg font-bold text-slate-900"
            >
              Upload Resume
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Add a PDF, TXT, or MD resume (max 10 MB) to your Resume Vault.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isUploading}
            aria-label="Close upload dialog"
            className="rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {formError ? (
          <div
            role="alert"
            className="mt-4 flex items-start gap-2.5 rounded-xl border border-destructive/25 bg-destructive-bg p-3.5 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{formError}</span>
          </div>
        ) : null}

        <form onSubmit={handleSubmit} noValidate className="mt-5 space-y-4">
          <FormField
            label="Resume title (optional)"
            name="resume-title"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (titleError) setTitleError("");
            }}
            placeholder="e.g. Senior Backend Engineer CV"
            hint="If left blank, your filename will be used."
            disabled={isUploading}
            error={titleError}
          />

          <FileDropzone
            file={file}
            onFileSelect={handleFileSelect}
            onClearFile={handleClearFile}
            error={fileError}
            disabled={isUploading}
          />

          {isUploading ? (
            <div className="space-y-1.5" aria-live="polite">
              <div className="flex justify-between text-xs font-medium text-slate-600">
                <span>Uploading resume...</span>
                <span className="font-mono tabular-nums">{uploadProgress}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-150"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          ) : null}

          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="secondary"
              size="md"
              disabled={isUploading}
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isUploading}
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  <span>Uploading...</span>
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" aria-hidden="true" />
                  <span>Upload Resume</span>
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

