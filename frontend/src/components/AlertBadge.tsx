"use client";

import { useEffect, useState } from "react";

export interface Alert {
  id: string;
  event_type: string;
  severity: "soft" | "medium" | "critical";
  message: string;
  created_at: string;
  rule_name?: string;
}

interface AlertBadgeProps {
  alerts: Alert[];
  maxVisible?: number;
  className?: string;
}

/**
 * AlertBadge: Displays live alerts as prominent web banners.
 * Critical alerts stay visible longer than medium/soft.
 */
export function AlertBadge({
  alerts,
  maxVisible = 3,
  className = "",
}: AlertBadgeProps) {
  const [activeAlertIds, setActiveAlertIds] = useState<Record<string, number>>(
    {},
  );

  useEffect(() => {
    const now = Date.now();
    setActiveAlertIds((prev) => {
      const next: Record<string, number> = { ...prev };
      for (const alert of alerts.slice(0, maxVisible)) {
        if (!next[alert.id]) {
          const durationMs =
            alert.severity === "critical"
              ? 6500
              : alert.severity === "medium"
                ? 4200
                : 2800;
          next[alert.id] = now + durationMs;
        }
      }
      return next;
    });
  }, [alerts, maxVisible]);

  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now();
      setActiveAlertIds((prev) => {
        let changed = false;
        const next: Record<string, number> = {};
        for (const [id, expiresAt] of Object.entries(prev)) {
          if (expiresAt > now) {
            next[id] = expiresAt;
          } else {
            changed = true;
          }
        }
        return changed ? next : prev;
      });
    }, 300);

    return () => clearInterval(timer);
  }, []);

  const visibleAlerts = alerts
    .slice(0, maxVisible)
    .filter((alert) => !!activeAlertIds[alert.id]);

  if (visibleAlerts.length === 0) {
    return null;
  }

  const severityStyles: Record<Alert["severity"], string> = {
    critical:
      "border-rose-300 bg-rose-600 text-white shadow-rose-400/35 ring-2 ring-rose-300/70",
    medium:
      "border-amber-200 bg-amber-500 text-white shadow-amber-300/35 ring-2 ring-amber-200/70",
    soft: "border-sky-200 bg-sky-500 text-white shadow-sky-300/30 ring-2 ring-sky-200/60",
  };

  const severityLabel: Record<Alert["severity"], string> = {
    critical: "Critical Alert",
    medium: "Warning",
    soft: "Notice",
  };

  return (
    <div
      className={`pointer-events-none fixed left-1/2 top-4 z-[60] flex w-[min(94vw,560px)] -translate-x-1/2 flex-col gap-3 ${className}`}
      role="status"
      aria-live="polite"
    >
      {visibleAlerts.map((alert) => (
        <div
          key={alert.id}
          className={`rounded-xl border px-4 py-3 shadow-xl backdrop-blur-sm ${severityStyles[alert.severity]}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.08em] opacity-95">
                {severityLabel[alert.severity]}
              </p>
              <p className="text-sm font-semibold leading-tight">
                {alert.rule_name || alert.event_type}
              </p>
            </div>
            <p className="text-[11px] font-medium opacity-90">
              {new Date(alert.created_at).toLocaleTimeString()}
            </p>
          </div>
          <p className="mt-1 text-sm leading-snug opacity-95">
            {alert.message}
          </p>

          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/25">
            <div className="h-full w-full animate-pulse rounded-full bg-white/80" />
          </div>
        </div>
      ))}
    </div>
  );
}
