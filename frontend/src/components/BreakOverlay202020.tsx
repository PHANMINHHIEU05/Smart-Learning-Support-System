"use client";

import { useMemo } from "react";

interface BreakOverlay202020Props {
  isOpen: boolean;
  secondsRemaining: number;
  onDismiss: () => void;
  onComplete: () => void;
}

function formatSeconds(seconds: number): string {
  const safe = Math.max(0, seconds);
  const m = Math.floor(safe / 60);
  const s = safe % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function BreakOverlay202020({
  isOpen,
  secondsRemaining,
  onDismiss,
  onComplete,
}: BreakOverlay202020Props) {
  const pct = useMemo(() => {
    const bounded = Math.min(20, Math.max(0, secondsRemaining));
    return Math.round(((20 - bounded) / 20) * 100);
  }, [secondsRemaining]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="surface-card surface-card-strong w-full max-w-md rounded-2xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold tracking-wider text-teal-700 uppercase">
            Eye Rest 20-20-20
          </p>
          <span className="text-xs text-slate-500">Optional</span>
        </div>

        <h2 className="text-xl font-bold text-slate-900">Look 20 feet away for 20 seconds</h2>
        <p className="text-sm text-slate-600">
          Keep your neck relaxed, blink slowly, and let your eyes reset.
        </p>

        <p className="text-5xl font-mono font-bold text-teal-700 text-center">
          {formatSeconds(secondsRemaining)}
        </p>

        <div className="w-full h-2.5 rounded-full bg-teal-100 overflow-hidden">
          <div
            className="h-full bg-teal-500 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>

        <div className="grid grid-cols-2 gap-3 pt-1">
          <button
            onClick={onDismiss}
            className="btn-soft"
          >
            Dismiss
          </button>
          <button
            onClick={onComplete}
            className="btn-primary"
          >
            Complete break
          </button>
        </div>
      </div>
    </div>
  );
}
