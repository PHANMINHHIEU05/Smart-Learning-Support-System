"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type {
  DailySummary,
  EnemyStats,
  FocusHeatmapCell,
  PenaltyHistoryResponse,
} from "@/types/api";

function toISODate(date: Date): string {
  return date.toISOString().split("T")[0];
}

function formatSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function last7Days(): string[] {
  const values: string[] = [];
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    values.push(toISODate(d));
  }
  return values;
}

function dayLabel(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function toPolyline(values: number[], width: number, height: number): string {
  if (values.length === 0) return "";
  const maxValue = Math.max(1, ...values);
  return values
    .map((value, i) => {
      const x = (i / Math.max(1, values.length - 1)) * width;
      const y = height - (value / maxValue) * height;
      return `${x},${y}`;
    })
    .join(" ");
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
  const [penaltyHistory, setPenaltyHistory] =
    useState<PenaltyHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const days = useMemo(() => last7Days(), []);

  useEffect(() => {
    setLoading(true);
    apiFetch<DailySummary>(
      `/api/v1/analytics/daily-summary?target_date=${selectedDate}`,
    )
      .then(setSummary)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedDate]);

  useEffect(() => {
    Promise.allSettled(
      days.map((d) =>
        apiFetch<DailySummary>(
          `/api/v1/analytics/daily-summary?target_date=${d}`,
        ),
      ),
    ).then((results) => {
      const mapped: Record<string, DailySummary> = {};
      results.forEach((result, i) => {
        if (result.status === "fulfilled") {
          mapped[days[i]] = result.value;
        }
      });
      setWeekData(mapped);
    });
  }, [days]);

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

  const focusByDay = useMemo(() => {
    return days.map((day) => ({
      day,
      focusSec: weekData[day]?.total_focus_seconds ?? 0,
      distractions: weekData[day]?.distraction_count ?? 0,
      fatigue: weekData[day]?.fatigue_count ?? 0,
    }));
  }, [days, weekData]);

  const postureProxyByDay = useMemo(() => {
    const byDay = Array.from({ length: 7 }, () => ({
      scoreTotal: 0,
      count: 0,
    }));
    for (const cell of focusHeatmap) {
      const idx = cell.day_of_week - 1;
      if (idx >= 0 && idx < 7) {
        byDay[idx].scoreTotal += cell.avg_focus_score;
        byDay[idx].count += 1;
      }
    }
    return byDay.map((item) =>
      item.count > 0 ? Math.round(item.scoreTotal / item.count) : 0,
    );
  }, [focusHeatmap]);

  const heatmapRows = useMemo(() => {
    const rows: FocusHeatmapCell[][] = Array.from({ length: 7 }, () => []);
    for (const cell of focusHeatmap) {
      const idx = cell.day_of_week - 1;
      if (idx >= 0 && idx < 7) {
        rows[idx].push(cell);
      }
    }
    for (const row of rows) {
      row.sort((a, b) => a.slot_index - b.slot_index);
    }
    return rows;
  }, [focusHeatmap]);

  const maxFocus = Math.max(1, ...focusByDay.map((d) => d.focusSec));
  const weeklyProductivity = Math.round(
    focusByDay.reduce(
      (acc, d) => acc + Math.min(100, (d.focusSec / 7200) * 100),
      0,
    ) / Math.max(1, focusByDay.length),
  );

  const slotTicks = ["00", "06", "12", "18"];
  const linePoints = toPolyline(postureProxyByDay, 560, 160);

  return (
    <div className="app-page fg-shell">
      <div className="page-header fg-header-card">
        <div>
          <h1 className="page-title fg-title-glow">Analytics Insights</h1>
          <p className="page-subtitle fg-muted-text">
            Vertical work rhythm, focus heatmap, and posture correlation trends.
          </p>
        </div>
      </div>

      <div className="fg-card">
        <div className="grid gap-3 md:grid-cols-3">
          <div>
            <label className="field-label">Daily Snapshot</label>
            <input
              type="date"
              value={selectedDate}
              max={toISODate(new Date())}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="field-input"
            />
          </div>
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

      {error && (
        <div className="rounded-xl border border-rose-400/40 bg-rose-500/15 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-4">
        <article className="fg-card">
          <p className="fg-kpi-label">Focus Time</p>
          <p className="fg-kpi-value">
            {loading
              ? "..."
              : summary
                ? formatSeconds(summary.total_focus_seconds)
                : "0m"}
          </p>
        </article>
        <article className="fg-card">
          <p className="fg-kpi-label">Distractions</p>
          <p className="fg-kpi-value">
            {loading ? "..." : (summary?.distraction_count ?? 0)}
          </p>
        </article>
        <article className="fg-card">
          <p className="fg-kpi-label">Fatigue Events</p>
          <p className="fg-kpi-value">
            {loading ? "..." : (summary?.fatigue_count ?? 0)}
          </p>
        </article>
        <article className="fg-card">
          <p className="fg-kpi-label">Weekly Productivity Score</p>
          <p className="fg-kpi-value" style={{ color: "#39FF14" }}>
            {weeklyProductivity}
          </p>
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <article className="fg-card">
          <header className="fg-card-head">
            <h2>Work Rhythm (Vertical Days)</h2>
            <span className="fg-chip">7 days</span>
          </header>
          <div className="fg-vertical-days">
            {focusByDay.map((item) => (
              <div key={item.day} className="fg-day-row">
                <div className="fg-day-col">
                  <p className="fg-day-label">{dayLabel(item.day)}</p>
                  <p className="fg-subtle">
                    {item.distractions} distractions | {item.fatigue} fatigue
                  </p>
                </div>
                <div className="fg-day-bar-wrap">
                  <div
                    className="fg-day-bar"
                    style={{
                      width: `${Math.max(4, Math.round((item.focusSec / maxFocus) * 100))}%`,
                    }}
                  />
                </div>
                <p className="fg-day-value">{formatSeconds(item.focusSec)}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="fg-card">
          <header className="fg-card-head">
            <h2>Posture Correlation vs Time</h2>
            <span className="fg-chip">Line proxy</span>
          </header>
          <div className="fg-linechart-wrap">
            <svg
              viewBox="0 0 560 200"
              className="fg-linechart"
              aria-label="posture correlation chart"
            >
              <defs>
                <linearGradient id="fgLineGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#00FFFF" />
                  <stop offset="100%" stopColor="#39FF14" />
                </linearGradient>
              </defs>
              <line
                x1="0"
                y1="160"
                x2="560"
                y2="160"
                stroke="rgba(245,245,245,0.25)"
              />
              <polyline
                fill="none"
                stroke="url(#fgLineGradient)"
                strokeWidth="3"
                points={linePoints}
              />
              {slotTicks.map((tick, i) => (
                <text
                  key={tick}
                  x={(i / (slotTicks.length - 1)) * 560}
                  y="190"
                  textAnchor="middle"
                  className="fg-chart-tick"
                >
                  {tick}:00
                </text>
              ))}
            </svg>
            <p className="fg-subtle">
              Correlation view uses focus stability over time to estimate
              posture consistency.
            </p>
          </div>
        </article>
      </section>

      <article className="fg-card">
        <header className="fg-card-head">
          <h2>Focus Heatmap</h2>
          <span className="fg-chip">Days arranged vertically</span>
        </header>
        <div className="fg-heatmap-shell">
          {heatmapRows.map((row, idx) => (
            <div key={idx} className="fg-heatmap-row">
              <div className="fg-heatmap-day">
                {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][idx]}
              </div>
              <div className="fg-heatmap-grid">
                {row.map((cell) => {
                  const focusedRatio =
                    cell.event_count > 0
                      ? cell.focused_event_count / cell.event_count
                      : 0;
                  const alpha =
                    cell.event_count === 0 ? 0.18 : 0.35 + focusedRatio * 0.5;
                  return (
                    <div
                      key={`${cell.day_of_week}-${cell.slot_index}`}
                      className="fg-heat-cell"
                      style={{
                        background: `rgba(0,255,255,${alpha})`,
                        borderColor: "rgba(75,0,130,0.55)",
                      }}
                      title={`${cell.slot_label} | score ${Math.round(cell.avg_focus_score)} | events ${cell.event_count}`}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </article>

      <article className="fg-card">
        <header className="fg-card-head">
          <h2>Penalty and Enemy Summary</h2>
        </header>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="fg-panel-soft">
            <p className="fg-kpi-label">Phone Detections</p>
            <p className="fg-kpi-value">
              {enemyStats?.phone_detected_count ?? 0}
            </p>
          </div>
          <div className="fg-panel-soft">
            <p className="fg-kpi-label">Drowsy + Slump</p>
            <p className="fg-kpi-value">
              {enemyStats?.drowsy_slump_count ?? 0}
            </p>
          </div>
          <div className="fg-panel-soft">
            <p className="fg-kpi-label">Penalties in Range</p>
            <p className="fg-kpi-value" style={{ color: "#FF0000" }}>
              {penaltyHistory?.total_penalties ?? 0}
            </p>
          </div>
        </div>
      </article>
    </div>
  );
}
