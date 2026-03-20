"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { EngagementSummary } from "@/types/api";

export function EngagementWidget() {
  const [summary, setSummary] = useState<EngagementSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch<EngagementSummary>("/api/v1/engagement/summary")
      .then(setSummary)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (error) {
    return (
      <div className="surface-card rounded-xl border border-amber-200 p-4 text-sm text-amber-700">
        Engagement data is temporarily unavailable.
      </div>
    );
  }

  return (
    <div className="surface-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">Focus Progress</h3>
        <span className="text-xs text-slate-500">
          {loading ? "..." : `Level ${summary?.current_level ?? 1}`}
        </span>
      </div>

      {/* Main net points display */}
      <div className="rounded-lg border border-cyan-200 bg-gradient-to-r from-cyan-50 to-sky-50 px-3 py-2">
        <p className="text-[10px] uppercase tracking-wide text-cyan-700">
          Net Points
        </p>
        <p className="mt-1 text-2xl font-bold text-cyan-900">
          {loading ? "..." : (summary?.points_net ?? 0)}
        </p>
      </div>

      {/* Earned vs Deducted breakdown */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-2 py-2">
          <p className="text-[10px] text-emerald-700 uppercase">Earned</p>
          <p className="text-lg font-bold text-emerald-900 mt-1">
            +{loading ? "..." : (summary?.points_earned ?? 0)}
          </p>
        </div>
        <div className="rounded-lg bg-red-50 border border-red-200 px-2 py-2">
          <p className="text-[10px] text-red-700 uppercase">Deducted</p>
          <p className="text-lg font-bold text-red-900 mt-1">
            -{loading ? "..." : (summary?.points_deducted ?? 0)}
          </p>
        </div>
      </div>

      {/* Other stats grid */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg border border-cyan-100 bg-cyan-50 px-2 py-2">
          <p className="text-[11px] text-cyan-700">Focus Blocks</p>
          <p className="text-lg font-bold text-cyan-900">
            {loading ? "..." : (summary?.completed_focus_blocks ?? 0)}
          </p>
        </div>
        <div className="rounded-lg border border-amber-100 bg-amber-50 px-2 py-2">
          <p className="text-[11px] text-amber-700">Next Level</p>
          <p className="text-lg font-bold text-amber-900">
            {loading ? "..." : (summary?.next_level_points ?? 100)}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 border border-slate-100 px-2 py-2">
          <p className="text-[11px] text-slate-700">Blocks/pts</p>
          <p className="text-lg font-bold text-slate-900">
            {loading ? "..." : (summary?.points_per_focus_block ?? 10)}
          </p>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <span>Level progress</span>
          <span>{loading ? "..." : `${summary?.progress_pct ?? 0}%`}</span>
        </div>
        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-sky-600 transition-all"
            style={{ width: `${loading ? 0 : (summary?.progress_pct ?? 0)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
