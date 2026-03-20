"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { DailySummary, EnemyStats, FocusHeatmapCell } from "@/types/api";

function formatSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function toISODate(date: Date): string {
  return date.toISOString().split("T")[0];
}

// Build last 7 days (Mon–Sun relative to today) for the bar chart
function last7Days(): string[] {
  const days: string[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(toISODate(d));
  }
  return days;
}

export default function AnalyticsPage() {
  const [selectedDate, setSelectedDate] = useState<string>(
    toISODate(new Date()),
  );
  const [dateFrom, setDateFrom] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() - 6);
    return toISODate(d);
  });
  const [dateTo, setDateTo] = useState<string>(toISODate(new Date()));
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [weekData, setWeekData] = useState<Record<string, DailySummary>>({});
  const [focusHeatmap, setFocusHeatmap] = useState<FocusHeatmapCell[]>([]);
  const [enemyStats, setEnemyStats] = useState<EnemyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch single-day summary whenever selectedDate changes
  useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch<DailySummary>(
      `/api/v1/analytics/daily-summary?target_date=${selectedDate}`,
    )
      .then(setSummary)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedDate]);

  // Fetch the last 7 days for the bar chart (fire-and-forget)
  useEffect(() => {
    const days = last7Days();
    Promise.allSettled(
      days.map((d) =>
        apiFetch<DailySummary>(
          `/api/v1/analytics/daily-summary?target_date=${d}`,
        ),
      ),
    ).then((results) => {
      const map: Record<string, DailySummary> = {};
      results.forEach((r, i) => {
        if (r.status === "fulfilled") map[days[i]] = r.value;
      });
      setWeekData(map);
    });
  }, []);

  useEffect(() => {
    setError(null);
    Promise.all([
      apiFetch<FocusHeatmapCell[]>(
        `/api/v1/analytics/focus-heatmap?date_from=${dateFrom}&date_to=${dateTo}`,
      ),
      apiFetch<EnemyStats>(
        `/api/v1/analytics/enemy-stats?date_from=${dateFrom}&date_to=${dateTo}`,
      ),
    ])
      .then(([heatmap, enemies]) => {
        setFocusHeatmap(heatmap);
        setEnemyStats(enemies);
      })
      .catch((e) => setError(e.message));
  }, [dateFrom, dateTo]);

  const days = last7Days();
  const maxFocusSec = Math.max(
    1,
    ...days.map((d) => weekData[d]?.total_focus_seconds ?? 0),
  );
  const maxHeatmapFocusSec = Math.max(
    1,
    ...focusHeatmap.map((cell) => cell.focus_seconds),
  );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Analytics</h1>

      {/* Date picker */}
      <div className="flex items-center gap-3 mb-6">
        <label className="text-sm font-medium text-gray-700">Date</label>
        <input
          type="date"
          value={selectedDate}
          max={toISODate(new Date())}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={() => setSelectedDate(toISODate(new Date()))}
          className="text-sm text-blue-600 hover:underline"
        >
          Today
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-gray-700">
            Range from
          </label>
          <input
            type="date"
            value={dateFrom}
            max={dateTo}
            onChange={(e) => setDateFrom(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-gray-700">Range to</label>
          <input
            type="date"
            value={dateTo}
            min={dateFrom}
            max={toISODate(new Date())}
            onChange={(e) => setDateTo(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Daily summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          {
            label: "Focus Time",
            value: loading
              ? "…"
              : summary
                ? formatSeconds(summary.total_focus_seconds)
                : "0m",
          },
          {
            label: "Sessions",
            value: loading ? "…" : (summary?.session_count ?? 0),
          },
          {
            label: "Distractions",
            value: loading ? "…" : (summary?.distraction_count ?? 0),
          },
          {
            label: "Fatigue Events",
            value: loading ? "…" : (summary?.fatigue_count ?? 0),
          },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-lg shadow p-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              {label}
            </p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          </div>
        ))}
      </div>

      {/* 7-day bar chart */}
      <div className="bg-white rounded-lg shadow p-5">
        <h2 className="font-semibold text-gray-800 mb-4">
          Focus Time — Last 7 Days
        </h2>
        <div className="flex items-end gap-2 h-32">
          {days.map((day) => {
            const data = weekData[day];
            const sec = data?.total_focus_seconds ?? 0;
            const pct = Math.round((sec / maxFocusSec) * 100);
            const label = new Date(day + "T00:00:00").toLocaleDateString(
              undefined,
              {
                weekday: "short",
              },
            );
            const isSelected = day === selectedDate;
            return (
              <button
                key={day}
                onClick={() => setSelectedDate(day)}
                className="flex-1 flex flex-col items-center gap-1 group"
                title={`${label}: ${formatSeconds(sec)}`}
              >
                <span className="text-xs text-gray-400 group-hover:text-blue-600">
                  {formatSeconds(sec)}
                </span>
                <div className="w-full flex items-end justify-center h-20">
                  <div
                    className={`w-full rounded-t transition-all ${
                      isSelected
                        ? "bg-blue-500"
                        : "bg-blue-200 group-hover:bg-blue-400"
                    }`}
                    style={{ height: `${Math.max(pct, 2)}%` }}
                  />
                </div>
                <span
                  className={`text-xs font-medium ${
                    isSelected ? "text-blue-600" : "text-gray-500"
                  }`}
                >
                  {label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Enemy stats */}
      <div className="bg-white rounded-lg shadow p-5 mt-6">
        <h2 className="font-semibold text-gray-800 mb-4">
          Top Distraction Enemies
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
          <div className="rounded border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-red-700 font-medium">Phone Detected</p>
            <p className="text-2xl font-bold text-red-900 mt-1">
              {enemyStats?.phone_detected_count ?? 0}
            </p>
            <p className="text-[11px] text-red-700 mt-1">
              Per session: {enemyStats?.phone_per_session ?? 0}
            </p>
          </div>
          <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-amber-700 font-medium">Phone + Book</p>
            <p className="text-2xl font-bold text-amber-900 mt-1">
              {enemyStats?.phone_book_count ?? 0}
            </p>
          </div>
          <div className="rounded border border-rose-200 bg-rose-50 px-4 py-3">
            <p className="text-rose-700 font-medium">Drowsy + Slump</p>
            <p className="text-2xl font-bold text-rose-900 mt-1">
              {enemyStats?.drowsy_slump_count ?? 0}
            </p>
          </div>
          <div className="rounded border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-slate-600 font-medium">Tracked AI Events</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">
              {enemyStats?.total_events ?? 0}
            </p>
          </div>
        </div>
      </div>

      {/* Focus heatmap by hour */}
      <div className="bg-white rounded-lg shadow p-5 mt-6">
        <h2 className="font-semibold text-gray-800 mb-4">
          Focus Heatmap by Hour
        </h2>
        <div className="grid grid-cols-6 md:grid-cols-12 gap-2">
          {focusHeatmap.map((cell) => {
            const intensity = Math.max(
              10,
              Math.round((cell.focus_seconds / maxHeatmapFocusSec) * 100),
            );
            return (
              <div
                key={cell.hour}
                className="rounded border border-blue-100 px-2 py-2"
                style={{ backgroundColor: `rgb(59 130 246 / ${intensity}%)` }}
                title={`Hour ${String(cell.hour).padStart(2, "0")}:00 · ${formatSeconds(
                  cell.focus_seconds,
                )} · Score ${Math.round(cell.avg_focus_score)}`}
              >
                <p className="text-xs font-semibold text-blue-950">
                  {String(cell.hour).padStart(2, "0")}:00
                </p>
                <p className="text-[11px] text-blue-900">
                  {formatSeconds(cell.focus_seconds)}
                </p>
                <p className="text-[10px] text-blue-900/80">
                  {Math.round(cell.avg_focus_score)}%
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
