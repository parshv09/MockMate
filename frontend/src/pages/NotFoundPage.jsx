import { Link } from "react-router-dom";
import { Card } from "../components/ui/Card.jsx";
import { Button } from "../components/ui/Button.jsx";

export function NotFoundPage() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center justify-center px-4">
      <Card className="w-full space-y-4 text-center">
        <p className="font-mono text-xs font-semibold text-primary">404 — ROUTE NOT FOUND</p>
        <h1 className="font-display text-xl font-bold text-foreground">
          Page not found
        </h1>
        <p className="text-sm text-foreground-secondary">
          The requested studio route does not exist. Return to the dashboard to continue.
        </p>
        <div className="pt-2">
          <Link to="/dashboard">
            <Button variant="primary">Return to Studio Overview</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}

