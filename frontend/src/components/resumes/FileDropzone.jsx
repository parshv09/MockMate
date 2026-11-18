import { useId, useRef, useState } from "react";
import { FileText, UploadCloud, X } from "lucide-react";
import {
  ALLOWED_RESUME_ACCEPT,
  formatFileSize,
} from "../../utils/resumeValidation.js";

export function FileDropzone({
  file = null,
  onFileSelect,
  onClearFile,
  error = "",
  disabled = false,
}) {
  const inputId = useId();
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFiles(fileList) {
    if (disabled || !fileList || fileList.length === 0) return;
    onFileSelect?.(fileList[0]);
  }

  function handleDragOver(event) {
    event.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  }

  function handleDragLeave(event) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    handleFiles(event.dataTransfer?.files);
  }

  function handleInputChange(event) {
    handleFiles(event.target.files);
    // Reset input value so re-selecting the same file after clearing still triggers onChange
    event.target.value = "";
  }

  return (
    <div className="space-y-2">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
          isDragging
            ? "border-primary bg-primary-subtle/70"
            : error
            ? "border-destructive/60 bg-destructive-bg/40"
            : "border-slate-300 bg-slate-50/70 hover:border-primary/60 hover:bg-slate-50"
        } ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
        onClick={() => {
          if (!disabled) inputRef.current?.click();
        }}
      >
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={ALLOWED_RESUME_ACCEPT}
          disabled={disabled}
          onChange={handleInputChange}
          aria-label="Choose resume file"
          className="sr-only"
        />

        {file ? (
          <div
            className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3.5 text-left shadow-xs"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-secondary-subtle text-secondary">
                <FileText className="h-5 w-5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900">
                  {file.name}
                </p>
                <p className="text-xs text-slate-500">{formatFileSize(file.size)}</p>
              </div>
            </div>

            {onClearFile && !disabled ? (
              <button
                type="button"
                onClick={onClearFile}
                aria-label="Remove selected file"
                className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            ) : null}
          </div>
        ) : (
          <div className="space-y-2">
            <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-primary-subtle text-primary">
              <UploadCloud className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">
                Drag and drop your resume here, or{" "}
                <span className="text-primary underline">browse files</span>
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Supports PDF, TXT, or MD up to 10 MB
              </p>
            </div>
          </div>
        )}
      </div>

      {error ? (
        <p role="alert" className="text-xs font-medium text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

