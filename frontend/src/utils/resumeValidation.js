/**
 * Client-side resume validation matching Django's validate_resume_file()
 * and ResumeUploadSerializer constraints.
 */

export const ALLOWED_RESUME_EXTENSIONS = [".pdf", ".txt", ".md"];
export const ALLOWED_RESUME_ACCEPT = ".pdf,.txt,.md,application/pdf,text/plain,text/markdown";
export const MAX_RESUME_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
export const MAX_RESUME_TITLE_LENGTH = 150;

export function getFileExtension(filename = "") {
  const lastDot = filename.lastIndexOf(".");
  if (lastDot <= 0) return "";
  return filename.slice(lastDot).toLowerCase();
}

export function validateResumeFileClient(file) {
  if (!file) {
    return { valid: false, error: "Please select a resume file to upload." };
  }

  const ext = getFileExtension(file.name || "");
  if (!ext || !ALLOWED_RESUME_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      error: `Unsupported file format${ext ? ` (${ext})` : ""}. Please upload a PDF, TXT, or MD file.`,
    };
  }

  if (typeof file.size === "number" && file.size > MAX_RESUME_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: "File size exceeds the 10 MB limit. Please choose a smaller file.",
    };
  }

  return { valid: true, error: "" };
}

export function formatFileSize(bytes) {
  if (typeof bytes !== "number" || !Number.isFinite(bytes) || bytes < 0) {
    return "";
  }
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

