import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import * as authApi from "../api/auth.api.js";
import * as resumesApi from "../api/resumes.api.js";
import { tokenStorage } from "../utils/tokenStorage.js";
import { MAX_RESUME_FILE_SIZE_BYTES } from "../utils/resumeValidation.js";

function renderResumesPage() {
  tokenStorage.setTokens({ access: "valid-access", refresh: "valid-refresh" });
  vi.spyOn(authApi, "fetchCurrentUser").mockResolvedValue({
    id: 1,
    username: "alexchen",
    email: "alex@example.com",
    first_name: "Alex",
    last_name: "Chen",
    user_type: "job_seeker",
    target_role: "Software Engineer",
  });

  return render(
    <AuthProvider>
      <ToastProvider>
        <MemoryRouter initialEntries={["/resumes"]}>
          <AppRoutes />
        </MemoryRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

const SAMPLE_RESUMES = [
  {
    id: 101,
    title: "Senior Backend Resume",
    file_name: "alex_backend.pdf",
    file_url: "http://127.0.0.1:8000/media/resumes/alex_backend.pdf",
    has_file: true,
    created_at: "2026-11-10T10:00:00Z",
    updated_at: "2026-11-12T10:00:00Z",
  },
  {
    id: 102,
    title: "Frontend Notes",
    file_name: "notes.md",
    file_url: "http://127.0.0.1:8000/media/resumes/notes.md",
    has_file: true,
    created_at: "2026-11-05T10:00:00Z",
    updated_at: "2026-11-05T10:00:00Z",
  },
];

describe("Resume Vault (/resumes)", () => {
  beforeEach(() => {
    tokenStorage.clearTokens();
    vi.restoreAllMocks();
  });

  it("renders saved resumes with filename and metadata", async () => {
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue(SAMPLE_RESUMES);

    renderResumesPage();

    expect(
      await screen.findByRole("heading", { name: /your resumes/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Senior Backend Resume")).toBeInTheDocument();
    expect(screen.getByText("alex_backend.pdf")).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
    expect(screen.getByText("Frontend Notes")).toBeInTheDocument();
    expect(screen.getByText("MD")).toBeInTheDocument();
    expect(screen.queryByText(/rag ready/i)).not.toBeInTheDocument();
  });

  it("renders empty state when user has no resumes", async () => {
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue([]);

    renderResumesPage();

    expect(
      await screen.findByText(/no resumes in your vault yet/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /upload your first resume/i })
    ).toBeInTheDocument();
  });

  it("renders API unavailable state and recovers on Retry", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes")
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce(SAMPLE_RESUMES);

    renderResumesPage();

    expect(
      await screen.findByText(/could not load resumes/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /retry/i }));

    expect(await screen.findByText("Senior Backend Resume")).toBeInTheDocument();
  });

  it("uploads a valid PDF resume and refreshes the list", async () => {
    const user = userEvent.setup();
    const uploadedItem = {
      id: 201,
      title: "Staff Engineer CV",
      file_name: "staff_cv.pdf",
      has_file: true,
      created_at: "2026-11-18T10:00:00Z",
      updated_at: "2026-11-18T10:00:00Z",
      text_length: 1200,
    };

    const fetchSpy = vi
      .spyOn(resumesApi, "fetchResumes")
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([uploadedItem]);

    const uploadSpy = vi
      .spyOn(resumesApi, "uploadResume")
      .mockResolvedValueOnce(uploadedItem);

    renderResumesPage();
    await screen.findByText(/no resumes in your vault yet/i);

    await user.click(screen.getByRole("button", { name: /^upload resume$/i }));

    const dialog = screen.getByRole("dialog", { name: /upload resume/i });
    await user.type(
      within(dialog).getByLabelText(/resume title/i),
      "Staff Engineer CV"
    );

    const pdfFile = new File(["%PDF-1.4\nResume content"], "staff_cv.pdf", {
      type: "application/pdf",
    });
    const fileInput = within(dialog).getByLabelText(/choose resume file/i);
    await user.upload(fileInput, pdfFile);

    await user.click(within(dialog).getByRole("button", { name: /upload resume/i }));

    await waitFor(() => {
      expect(uploadSpy).toHaveBeenCalledTimes(1);
    });
    expect(uploadSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Staff Engineer CV",
        file: pdfFile,
      })
    );
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("Staff Engineer CV")).toBeInTheDocument();
  });

  it("uploads valid TXT and MD resumes", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue([]);
    const uploadSpy = vi.spyOn(resumesApi, "uploadResume").mockResolvedValue({
      id: 202,
      title: "Plain Resume",
      file_name: "resume.txt",
      has_file: true,
      created_at: "2026-11-18T10:00:00Z",
      updated_at: "2026-11-18T10:00:00Z",
    });

    renderResumesPage();
    await screen.findByRole("heading", { name: /your resumes/i });

    // 1. TXT upload
    await user.click(screen.getByRole("button", { name: /^upload resume$/i }));
    let dialog = screen.getByRole("dialog");
    const txtFile = new File(["Experienced engineer"], "resume.txt", {
      type: "text/plain",
    });
    await user.upload(within(dialog).getByLabelText(/choose resume file/i), txtFile);
    await user.click(within(dialog).getByRole("button", { name: /upload resume/i }));
    await waitFor(() => expect(uploadSpy).toHaveBeenCalledTimes(1));

    // 2. MD upload
    await user.click(screen.getByRole("button", { name: /^upload resume$/i }));
    dialog = screen.getByRole("dialog");
    const mdFile = new File(["# Resume\n- Python"], "resume.md", {
      type: "text/markdown",
    });
    await user.upload(within(dialog).getByLabelText(/choose resume file/i), mdFile);
    await user.click(within(dialog).getByRole("button", { name: /upload resume/i }));
    await waitFor(() => expect(uploadSpy).toHaveBeenCalledTimes(2));
  });

  it("rejects unsupported file extensions and files over 10 MB", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue([]);
    const uploadSpy = vi.spyOn(resumesApi, "uploadResume");

    renderResumesPage();
    await screen.findByRole("heading", { name: /your resumes/i });

    await user.click(screen.getByRole("button", { name: /^upload resume$/i }));
    const dialog = screen.getByRole("dialog");
    const fileInput = within(dialog).getByLabelText(/choose resume file/i);

    // Unsupported extension (.docx) - remove accept temporarily for test upload simulation if needed
    fileInput.removeAttribute("accept");
    const unsupportedFile = new File(["docx bytes"], "resume.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    await user.upload(fileInput, unsupportedFile);
    expect(
      within(dialog).getByText(/unsupported file format/i)
    ).toBeInTheDocument();

    // Oversized file (> 10 MB)
    const oversizedFile = new File(["x"], "huge.pdf", { type: "application/pdf" });
    Object.defineProperty(oversizedFile, "size", {
      value: MAX_RESUME_FILE_SIZE_BYTES + 1,
    });
    await user.upload(fileInput, oversizedFile);
    expect(
      within(dialog).getByText(/exceeds the 10 mb limit/i)
    ).toBeInTheDocument();

    expect(uploadSpy).not.toHaveBeenCalled();
  });

  it("surfaces backend upload errors without closing the modal", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue([]);
    vi.spyOn(resumesApi, "uploadResume").mockRejectedValueOnce({
      response: {
        status: 400,
        data: {
          file: ["Invalid PDF file content. The file does not have a valid %PDF header."],
        },
      },
    });

    renderResumesPage();
    await screen.findByRole("heading", { name: /your resumes/i });

    await user.click(screen.getByRole("button", { name: /^upload resume$/i }));
    const dialog = screen.getByRole("dialog");
    const badPdf = new File(["not really pdf"], "bad.pdf", {
      type: "application/pdf",
    });
    await user.upload(within(dialog).getByLabelText(/choose resume file/i), badPdf);
    await user.click(within(dialog).getByRole("button", { name: /upload resume/i }));

    expect(
      await within(dialog).findAllByText(/invalid pdf file content/i)
    ).not.toHaveLength(0);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("confirms and deletes a resume, and keeps it if deletion fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(resumesApi, "fetchResumes").mockResolvedValue(SAMPLE_RESUMES);
    const deleteSpy = vi
      .spyOn(resumesApi, "deleteResume")
      .mockRejectedValueOnce({
        response: { status: 500, data: { detail: "Server error" } },
      })
      .mockResolvedValueOnce(undefined);

    renderResumesPage();
    await screen.findByText("Senior Backend Resume");

    // 1. Open confirmation and cancel
    await user.click(
      screen.getByRole("button", { name: /delete senior backend resume/i })
    );
    let dialog = screen.getByRole("dialog", { name: /delete resume/i });
    await user.click(within(dialog).getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(deleteSpy).not.toHaveBeenCalled();

    // 2. Confirm delete -> backend fails -> resume stays in list
    await user.click(
      screen.getByRole("button", { name: /delete senior backend resume/i })
    );
    dialog = screen.getByRole("dialog", { name: /delete resume/i });
    await user.click(within(dialog).getByRole("button", { name: /delete resume/i }));

    await waitFor(() => expect(deleteSpy).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Senior Backend Resume")).toBeInTheDocument();

    // 3. Retry delete -> succeeds -> resume removed
    await user.click(within(dialog).getByRole("button", { name: /delete resume/i }));
    await waitFor(() => {
      expect(screen.queryByText("Senior Backend Resume")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Frontend Notes")).toBeInTheDocument();
  });
});

