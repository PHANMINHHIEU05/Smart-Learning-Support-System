"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type {
  DailySummary,
  EngagementSummary,
  EnemyStats,
  FocusHeatmapCell,
  PenaltyHistoryResponse,
} from "@/types/api";

function formatSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function toISODate(date: Date): string {
  return date.toISOString().split("T")[0];
}

function last7Days(): string[] {
  const days: string[] = [];
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(toISODate(d));
  }
  return days;
}

interface TileProps {
  label: string;
  value: string | number;
}

function Tile({ label, value }: TileProps) {
  return (
    <div className="metric-tile">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
    </div>
  );
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
  const [engagementSummary, setEngagementSummary] =
    useState<EngagementSummary | null>(null);
  const [penaltyHistory, setPenaltyHistory] =
    useState<PenaltyHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      results.forEach((result, i) => {
        if (result.status === "fulfilled") {
          map[days[i]] = result.value;
        }
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
      apiFetch<PenaltyHistoryResponse>(
        `/api/v1/engagement/penalty-history?date_from=${dateFrom}&date_to=${dateTo}`,
      ),
    ])
      .then(([heatmap, enemies, penalties]) => {
        setFocusHeatmap(heatmap);
        setEnemyStats(enemies);
        setPenaltyHistory(penalties);
      })
      .catch((e) => setError(e.message));
  }, [dateFrom, dateTo]);

  useEffect(() => {
    setError(null);
    apiFetch<EngagementSummary>("/api/v1/engagement/summary")
      .then(setEngagementSummary)
      .catch((e) => setError(e.message));
  }, []);

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
    <div className="app-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Track focus trends, penalties, and distraction patterns.</p>
        </div>
      </div>

      <div className="surface-card p-4 md:p-5">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="field-label">Daily Snapshot</label>
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={selectedDate}
                max={toISODate(new Date())}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="field-input"
              />
              <button
                onClick={() => setSelectedDate(toISODate(new Date()))}
                className="btn-soft whitespace-nowrap px-3 py-2"
              >
                Today
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="field-label">Range From</label>
              <input
                type="date"
                value={dateFrom}
                max={dateTo}
                onChange={(e) => setDateFrom(e.target.value)}
                className="field-input"
              />
            </div>
            <div>
              <label className="field-label">Range To</label>
              <input
                type="date"
                value={dateTo}
                min={dateFrom}
                max={toISODate(new Date())}
                onChange={(e) => setDateTo(e.target.value)}
                className="field-input"
              />
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Tile
          label="Focus Time"
          value={
            loading
              ? "..."
              : summary
                ? formatSeconds(summary.total_focus_seconds)
                : "0m"
          }
        />
        <Tile label="Sessions" value={loading ? "..." : (summary?.session_count ?? 0)} />
        <Tile
          label="Distractions"
          value={loading ? "..." : (summary?.distraction_count ?? 0)}
        />
        <Tile
          label="Fatigue Events"
          value={loading ? "..." : (summary?.fatigue_count ?? 0)}
        />
      </div>

      <div className="surface-card p-5 md:p-6">
        <h2 className="text-xl font-bold text-slate-900">Focus Time - Last 7 Days</h2>
        <div className="mt-4 flex h-36 items-end gap-2">
          {days.map((day) => {
            const data = weekData[day];
            const sec = data?.total_focus_seconds ?? 0;
            const pct = Math.round((sec / maxFocusSec) * 100);
            const label = new Date(`${day}T00:00:00`).toLocaleDateString(
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
                className="group flex flex-1 flex-col items-center gap-1"
                title={`${label}: ${formatSeconds(sec)}`}
              >
                <span className="text-xs text-slate-500 group-hover:text-cyan-700">
                  {formatSeconds(sec)}
                </span>
                <div className="flex h-24 w-full items-end justify-center rounded-lg bg-slate-100/70 p-1">
                  <div
                    className={`w-full rounded-md transition-all ${
                      isSelected
                        ? "bg-gradient-to-t from-cyan-600 to-sky-500"
                        : "bg-gradient-to-t from-cyan-300 to-sky-300 group-hover:from-cyan-500 group-hover:to-sky-500"
                    }`}
                    style={{ height: `${Math.max(pct, 3)}%` }}
                  />
                </div>
                <span
                  className={`text-xs font-semibold ${
                    isSelected ? "text-cyan-700" : "text-slate-500"
                  }`}
                >
                  {label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="surface-card p-5 md:p-6">
        <h2 className="text-xl font-bold text-slate-900">Engagement Score</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-5 text-sm">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
            <p className="font-semibold text-emerald-700">Points Earned</p>
            <p className="mt-1 text-2xl font-bold text-emerald-900">
              {engagementSummary?.points_earned ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3">
            <p className="font-semibold text-rose-700">Points Deducted</p>
            <p className="mt-1 text-2xl font-bold text-rose-900">
              {engagementSummary?.points_deducted ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-3">
            <p className="font-semibold text-cyan-700">Net Points</p>
            <p className="mt-1 text-2xl font-bold text-cyan-900">
              {engagementSummary?.points_net ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3">
            <p className="font-semibold text-indigo-700">Current Level</p>
            <p className="mt-1 text-2xl font-bold text-indigo-900">
              {engagementSummary?.current_level ?? 1}
            </p>
          </div>
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="font-semibold text-amber-700">Range Penalties</p>
            <p className="mt-1 text-2xl font-bold text-amber-900">
              {penaltyHistory?.total_penalties ?? 0}
            </p>
            <p className="mt-1 text-[11px] text-amber-700">
              Events: {penaltyHistory?.events.length ?? 0}
            </p>
          </div>
        </div>
      </div>

      <div className="surface-card p-5 md:p-6">
        <h2 className="text-xl font-bold text-slate-900">Top Distraction Enemies</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4 text-sm">
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3">
            <p className="font-semibold text-rose-700">Phone Detected</p>
            <p className="mt-1 text-2xl font-bold text-rose-900">
              {enemyStats?.phone_detected_count ?? 0}
            </p>
            <p className="mt-1 text-[11px] text-rose-700">
              Per session: {enemyStats?.phone_per_session ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="font-semibold text-amber-700">Phone + Book</p>
            <p className="mt-1 text-2xl font-bold text-amber-900">
              {enemyStats?.phone_book_count ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-fuchsia-200 bg-fuchsia-50 px-4 py-3">
            <p className="font-semibold text-fuchsia-700">Drowsy + Slump</p>
            <p className="mt-1 text-2xl font-bold text-fuchsia-900">
              {enemyStats?.drowsy_slump_count ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="font-semibold text-slate-700">Tracked AI Events</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {enemyStats?.total_events ?? 0}
            </p>
          </div>
        </div>
      </div>

      <div className="surface-card p-5 md:p-6">
        <h2 className="text-xl font-bold text-slate-900">
          Penalty History (Selected Range)
        </h2>
        {penaltyHistory && penaltyHistory.events.length > 0 ? (
          <div className="mt-4 space-y-2">
            {penaltyHistory.events.slice(0, 8).map((event) => (
              <div
                key={`${event.event_id ?? "no-id"}-${event.event_time}`}
                className="flex items-center justify-between rounded-xl border border-slate-200/80 bg-white/70 px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-semibold text-slate-800">{event.event_type}</p>
                  <p className="text-xs text-slate-500">
                    {new Date(event.event_time).toLocaleString()}
                  </p>
                </div>
                <span className="font-bold text-rose-700">-{event.points_deducted}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">No penalty events in this range.</p>
        )}
      </div>

      <div className="surface-card p-5 md:p-6">
        <h2 className="text-xl font-bold text-slate-900">Focus Heatmap by Hour</h2>
        <div className="mt-4 grid grid-cols-6 gap-2 md:grid-cols-12">
          {focusHeatmap.map((cell) => {
            const intensity = Math.max(
              10,
              Math.round((cell.focus_seconds / maxHeatmapFocusSec) * 100),
            );
            return (
              <div
                key={cell.hour}
                className="rounded-xl border border-cyan-100 px-2 py-2"
                style={{ backgroundColor: `rgb(14 165 233 / ${intensity}%)` }}
                title={`Hour ${String(cell.hour).padStart(2, "0")}:00 - ${formatSeconds(
                  cell.focus_seconds,
                )} - Score ${Math.round(cell.avg_focus_score)}`}
              >
                <p className="text-xs font-semibold text-sky-950">
                  {String(cell.hour).padStart(2, "0")}:00
                </p>
                <p className="text-[11px] text-sky-900">
                  {formatSeconds(cell.focus_seconds)}
                </p>
                <p className="text-[10px] text-sky-900/80">
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
