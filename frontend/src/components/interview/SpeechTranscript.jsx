import { CheckCircle2, FileAudio, MessageSquareText, X } from "lucide-react";

/**
 * Displays the speech-to-text transcription and evaluation feedback returned
 * synchronously by POST /api/v1/sessions/<id>/answers/.
 */
export function SpeechTranscript({ evaluation = null, onDismiss }) {
  if (!evaluation) return null;

  const hasScore =
    typeof evaluation.score === "number" && Number.isFinite(evaluation.score);
  const transcriptText = (evaluation.answer_text || "").trim();
  const isVoiceAnswer = Boolean(evaluation.has_audio);
  const tips = Array.isArray(evaluation.improvement_tips)
    ? evaluation.improvement_tips.filter(Boolean)
    : [];

  return (
    <section
      aria-label="Previous answer evaluation"
      className="space-y-3 rounded-2xl border border-teal-600/25 bg-secondary-subtle/60 p-4 shadow-xs sm:p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-secondary" aria-hidden="true" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-secondary">
            Question {evaluation.index} Evaluated
          </h2>
          {isVoiceAnswer ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-teal-700/15 px-2.5 py-0.5 text-[11px] font-semibold text-secondary">
              <FileAudio className="h-3 w-3" aria-hidden="true" />
              Voice Transcribed
            </span>
          ) : null}
          {hasScore ? (
            <span className="rounded-full bg-white px-2.5 py-0.5 font-mono text-xs font-bold text-slate-900 shadow-2xs tabular-nums">
              Score: {Math.round(evaluation.score)}%
            </span>
          ) : null}
        </div>

        {onDismiss ? (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss evaluation feedback"
            className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium text-slate-500 hover:bg-white/60 hover:text-slate-800"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Dismiss</span>
          </button>
        ) : null}
      </div>

      {/* Recognized Speech-to-Text Transcript */}
      {isVoiceAnswer && transcriptText ? (
        <div
          aria-label="Recognized speech transcript"
          className="rounded-xl border border-teal-700/15 bg-white/90 p-3 text-xs text-slate-700"
        >
          <p className="flex items-center gap-1.5 font-semibold text-slate-900">
            <MessageSquareText className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
            <span>Recognized Speech Transcript</span>
          </p>
          <p className="mt-1 leading-relaxed text-slate-700">
            &ldquo;{transcriptText}&rdquo;
          </p>
        </div>
      ) : null}

      {evaluation.feedback ? (
        <p className="text-sm leading-relaxed text-slate-700">
          {evaluation.feedback}
        </p>
      ) : null}

      {tips.length > 0 ? (
        <ul className="space-y-1 text-xs text-slate-600">
          {tips.slice(0, 2).map((tip, idx) => (
            <li key={idx} className="flex items-start gap-2">
              <span
                className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary"
                aria-hidden="true"
              />
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

