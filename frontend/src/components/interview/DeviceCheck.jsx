import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Mic,
  Settings2,
  Video,
} from "lucide-react";
import { useMediaDevices } from "../../hooks/useMediaDevices.js";

const STATUS_BADGE = {
  idle: { text: "Not tested", className: "bg-slate-100 text-slate-600" },
  checking: { text: "Checking...", className: "bg-primary-subtle text-primary" },
  ready: { text: "Ready", className: "bg-success-bg text-success" },
  denied: { text: "Blocked", className: "bg-destructive-bg text-destructive" },
  unavailable: { text: "Unavailable", className: "bg-warning-bg text-warning" },
};

export function DeviceCheck() {
  const [isOpen, setIsOpen] = useState(false);
  const {
    micStatus,
    cameraStatus,
    deviceError,
    checkMicrophone,
    checkCamera,
  } = useMediaDevices();

  const micBadge = STATUS_BADGE[micStatus] || STATUS_BADGE.idle;
  const camBadge = STATUS_BADGE[cameraStatus] || STATUS_BADGE.idle;

  return (
    <section
      aria-label="Microphone and camera setup check"
      className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm"
    >
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <div className="flex items-center gap-2">
          <Settings2 className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="font-display text-sm font-bold text-slate-900">
            Audio &amp; Camera Check
          </span>
        </div>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-slate-500" aria-hidden="true" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-500" aria-hidden="true" />
        )}
      </button>

      {isOpen ? (
        <div className="mt-4 space-y-3 border-t border-slate-200/80 pt-3 text-xs">
          <p className="text-slate-600">
            Verify your microphone and camera before recording. You can switch between voice and text answers at any time.
          </p>

          {deviceError ? (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-destructive/25 bg-destructive-bg p-2.5 text-destructive"
            >
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>{deviceError}</span>
            </div>
          ) : null}

          <div className="space-y-2">
            <div className="flex items-center justify-between rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
              <div className="flex items-center gap-2">
                <Mic className="h-4 w-4 text-primary" aria-hidden="true" />
                <span className="font-medium text-slate-800">Microphone</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${micBadge.className}`}>
                  {micBadge.text}
                </span>
              </div>
              <button
                type="button"
                disabled={micStatus === "checking"}
                onClick={checkMicrophone}
                className="rounded-md border border-slate-300 bg-white px-2.5 py-1 font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
              >
                Test Mic
              </button>
            </div>

            <div className="flex items-center justify-between rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
              <div className="flex items-center gap-2">
                <Video className="h-4 w-4 text-secondary" aria-hidden="true" />
                <span className="font-medium text-slate-800">Camera</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${camBadge.className}`}>
                  {camBadge.text}
                </span>
              </div>
              <button
                type="button"
                disabled={cameraStatus === "checking"}
                onClick={checkCamera}
                className="rounded-md border border-slate-300 bg-white px-2.5 py-1 font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
              >
                Test Camera
              </button>
            </div>
          </div>

          <div className="rounded-xl bg-primary-subtle/50 p-2.5 text-slate-700">
            <p className="flex items-center gap-1.5 font-semibold text-primary">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Studio Guidelines</span>
            </p>
            <p className="mt-1 leading-relaxed">
              Questions are answered sequentially. Listen to the prompt, record your voice or type your answer, and review your audio before submitting.
            </p>
          </div>
        </div>
      ) : null}
    </section>
  );
}

