import { FileText } from "lucide-react";
import { Card } from "../ui/Card.jsx";
import { Badge } from "../ui/Badge.jsx";

export function ResumeCard({ title = "Resume Document", status = "RAG Ready" }) {
  return (
    <Card className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-secondary-subtle text-secondary">
          <FileText className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          <p className="text-xs text-foreground-muted">Resume Vault placeholder card</p>
        </div>
      </div>
      <Badge tone="teal">{status}</Badge>
    </Card>
  );
}

