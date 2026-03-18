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
      <div className="bg-white rounded-xl shadow p-4 text-sm text-amber-700 border border-amber-200">
        Engagement data is temporarily unavailable.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">Focus Progress</h3>
        <span className="text-xs text-slate-500">
          {loading ? "..." : `Level ${summary?.current_level ?? 1}`}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-blue-50 border border-blue-100 px-2 py-2">
          <p className="text-[11px] text-blue-700">Points</p>
          <p className="text-lg font-bold text-blue-900">
            {loading ? "..." : (summary?.total_points ?? 0)}
          </p>
        </div>
        <div className="rounded-lg bg-emerald-50 border border-emerald-100 px-2 py-2">
          <p className="text-[11px] text-emerald-700">Focus Blocks</p>
          <p className="text-lg font-bold text-emerald-900">
            {loading ? "..." : (summary?.completed_focus_blocks ?? 0)}
          </p>
        </div>
        <div className="rounded-lg bg-violet-50 border border-violet-100 px-2 py-2">
          <p className="text-[11px] text-violet-700">Next Level</p>
          <p className="text-lg font-bold text-violet-900">
            {loading ? "..." : (summary?.next_level_points ?? 100)}
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
            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all"
            style={{ width: `${loading ? 0 : (summary?.progress_pct ?? 0)}%` }}
          />
        </div>
      </div>

      <p className="text-[11px] text-slate-500">
        {loading
          ? "Loading..."
          : `${summary?.points_per_focus_block ?? 10} points per completed focus block.`}
      </p>
    </div>
  );
}
