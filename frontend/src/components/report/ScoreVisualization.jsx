import { useMemo } from "react";

export function getScoreTone(score) {
  if (typeof score !== "number" || isNaN(score)) return "neutral";
  if (score >= 80) return "success";
  if (score >= 65) return "primary";
  if (score >= 50) return "warning";
  return "destructive";
}

export function getScoreLabel(score) {
  if (typeof score !== "number" || isNaN(score)) return "Awaiting Score";
  if (score >= 85) return "Exceptional";
  if (score >= 75) return "Strong Performance";
  if (score >= 65) return "Proficient";
  if (score >= 50) return "Developing";
  return "Needs Improvement";
}

const TONE_COLORS = {
  success: {
    stroke: "#15803D", // Success Green
    text: "text-emerald-700",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
  primary: {
    stroke: "#1D4ED8", // Studio Cobalt
    text: "text-blue-700",
    bg: "bg-blue-50",
    border: "border-blue-200",
  },
  warning: {
    stroke: "#B45309", // Amber 700
    text: "text-amber-800",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  destructive: {
    stroke: "#B91C1C", // Destructive Red
    text: "text-rose-700",
    bg: "bg-rose-50",
    border: "border-rose-200",
  },
  neutral: {
    stroke: "#94A3B8",
    text: "text-slate-600",
    bg: "bg-slate-100",
    border: "border-slate-200",
  },
};

/**
 * Circular score gauge with calibrated stroke animation.
 */
export function ScoreGauge({
  score = null,
  size = 140,
  strokeWidth = 10,
  label = "Overall Score",
  showSubtext = true,
  className = "",
}) {
  const safeScore = typeof score === "number" && !isNaN(score) ? Math.min(100, Math.max(0, score)) : null;
  const tone = getScoreTone(safeScore);
  const color = TONE_COLORS[tone] || TONE_COLORS.neutral;

  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset =
    safeScore !== null ? circumference - (safeScore / 100) * circumference : circumference;

  return (
    <div className={`flex flex-col items-center text-center ${className}`.trim()}>
      <div className="relative inline-flex items-center justify-center">
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="rotate-[-90deg] transform"
          aria-hidden="true"
        >
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="transparent"
            className="text-slate-200"
          />
          {/* Colored Score Arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color.stroke}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Inner Score Label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-3xl font-extrabold tracking-tight text-foreground">
            {safeScore !== null ? Math.round(safeScore) : "—"}
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-foreground-muted">
            / 100
          </span>
        </div>
      </div>

      {label ? <p className="mt-2.5 text-xs font-semibold text-foreground">{label}</p> : null}
      {showSubtext ? (
        <span
          className={`mt-1 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${color.bg} ${color.text} border ${color.border}`}
        >
          {getScoreLabel(safeScore)}
        </span>
      ) : null}
    </div>
  );
}

