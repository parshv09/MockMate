import { Link } from "react-router-dom";
import { ArrowLeft, FileText } from "lucide-react";
import { Button } from "../components/ui/Button.jsx";

export function ResumesPage() {
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#070D19] via-[#0B1528] to-[#0F1D3A] p-6 text-white shadow-lg sm:p-8">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <span className="inline-flex items-center rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-teal-300">
              Resume Vault
            </span>
            <h1 className="mt-2 font-display text-2xl font-bold tracking-tight text-white">
              Your Resumes
            </h1>
            <p className="mt-1 text-sm text-slate-300">
              Upload and manage resumes to tailor your interview questions.
            </p>
          </div>

          <Link to="/dashboard">
            <Button
              variant="secondary"
              size="sm"
              className="border-white/20 bg-white/10 text-white hover:bg-white/20"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              <span>Back to Dashboard</span>
            </Button>
          </Link>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200/80 bg-white py-12 text-center shadow-sm">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary-subtle text-secondary">
          <FileText className="h-6 w-6" aria-hidden="true" />
        </div>
        <h2 className="mt-4 font-display text-base font-bold text-slate-900">
          Resume upload & management coming next
        </h2>
        <p className="mt-1 max-w-md text-sm text-slate-600">
          This protected workspace is ready for the Resume Management workflow in the next implementation step.
        </p>
      </div>
    </div>
  );
}
