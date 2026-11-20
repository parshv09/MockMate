import { Loader2, Send, SkipForward } from "lucide-react";
import { Button } from "../ui/Button.jsx";

export function InterviewControls({
  isSubmitting = false,
  isSkipping = false,
  isEnding = false,
  canSubmit = true,
  onSkip,
}) {
  const isBusy = isSubmitting || isSkipping || isEnding;

  return (
    <div className="flex flex-col-reverse items-stretch justify-between gap-3 border-t border-slate-200/80 pt-4 sm:flex-row sm:items-center">
      <Button
        type="button"
        variant="secondary"
        size="md"
        isLoading={isSkipping}
        disabled={isBusy}
        onClick={onSkip}
      >
        {isSkipping ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            <span>Skipping...</span>
          </>
        ) : (
          <>
            <SkipForward className="h-4 w-4" aria-hidden="true" />
            <span>Skip Question</span>
          </>
        )}
      </Button>

      <Button
        type="submit"
        variant="primary"
        size="lg"
        isLoading={isSubmitting}
        disabled={isBusy || !canSubmit}
        className="shadow-md"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            <span>Submitting Answer...</span>
          </>
        ) : (
          <>
            <Send className="h-4 w-4" aria-hidden="true" />
            <span>Submit Answer</span>
          </>
        )}
      </Button>
    </div>
  );
}

