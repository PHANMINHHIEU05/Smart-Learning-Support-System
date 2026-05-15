"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api-client";
import type {
  AiEventResponse,
  DailySummary,
  EnemyStats,
  Task,
  UserSetting,
} from "@/types/api";

function formatSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function formatEventTime(value: string): string {
  const d = new Date(value);
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [enemyStats, setEnemyStats] = useState<EnemyStats | null>(null);
  const [settings, setSettings] = useState<UserSetting | null>(null);
  const [recentEvents, setRecentEvents] = useState<AiEventResponse[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    router.prefetch("/timer");
  }, [router]);

  useEffect(() => {
    const today = new Date().toISOString().split("T")[0];
    Promise.all([
      apiFetch<DailySummary>(
        `/api/v1/analytics/daily-summary?target_date=${today}`,
      ),
      apiFetch<EnemyStats>(
        `/api/v1/analytics/enemy-stats?date_from=${today}&date_to=${today}`,
      ),
      apiFetch<UserSetting>("/api/v1/settings/"),
      apiFetch<AiEventResponse[]>("/api/v1/ai-events/?limit=8"),
      apiFetch<Task[]>("/api/v1/tasks/?status=todo&limit=5"),
    ])
      .then(([sum, enemies, userSettings, events, taskList]) => {
        setSummary(sum);
        setEnemyStats(enemies);
        setSettings(userSettings);
        setRecentEvents(events ?? []);
        setTasks(taskList ?? []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const dailyGoalMinutes = settings?.daily_goal_minutes ?? 120;
  const focusedMinutes = Math.round((summary?.total_focus_seconds ?? 0) / 60);
  const goalPct = Math.max(
    0,
    Math.min(
      100,
      Math.round((focusedMinutes / Math.max(1, dailyGoalMinutes)) * 100),
    ),
  );

  const pomodoroRingPct = useMemo(() => {
    const minutes = settings?.pomodoro_focus_minutes ?? 25;
    const completed = Math.min(minutes, focusedMinutes);
    return Math.round((completed / Math.max(1, minutes)) * 100);
  }, [focusedMinutes, settings?.pomodoro_focus_minutes]);

  const healthyState = (enemyStats?.phone_per_session ?? 0) <= 1;

  return (
    <div className="app-page fg-shell">
      <div className="page-header fg-header-card">
        <div>
          <h1 className="page-title fg-title-glow">FocusGuardian Dashboard</h1>
          <p className="page-subtitle fg-muted-text">
            Real-time posture, timer rhythm, and focus insights in one view.
          </p>
        </div>
        <Link
          href="/timer"
          prefetch
          onMouseEnter={() => router.prefetch("/timer")}
          onFocus={() => router.prefetch("/timer")}
          className="fg-cta"
        >
          Start Session
        </Link>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-400/40 bg-rose-500/15 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      <section className="fg-bento-grid">
        <article className="fg-card fg-card-wireframe">
          <header className="fg-card-head">
            <h2>AI Posture Monitor</h2>
            <span className={`fg-status-dot ${healthyState ? "ok" : "alert"}`}>
              {healthyState ? "Healthy" : "Watch posture"}
            </span>
          </header>
          <div className="fg-wireframe-wrap">
            <svg
              viewBox="0 0 220 160"
              className="fg-wireframe"
              aria-label="posture wireframe"
            >
              <circle cx="110" cy="34" r="18" />
              <line x1="110" y1="52" x2="110" y2="102" />
              <line x1="72" y1="72" x2="148" y2="72" />
              <line x1="110" y1="102" x2="84" y2="142" />
              <line x1="110" y1="102" x2="136" y2="142" />
              <circle cx="84" cy="142" r="4" />
              <circle cx="136" cy="142" r="4" />
              <circle cx="72" cy="72" r="4" />
              <circle cx="148" cy="72" r="4" />
            </svg>
            <p className="fg-subtle">
              Lightweight vector posture scaffold for better performance on
              low-end devices.
            </p>
          </div>
        </article>

        <article className="fg-card fg-card-timer">
          <header className="fg-card-head">
            <h2>Pomodoro Ring</h2>
            <span className="fg-chip">
              {settings?.pomodoro_focus_minutes ?? 25} min
            </span>
          </header>
          <div className="fg-ring-wrap">
            <div
              className="fg-ring"
              style={{
                background: `conic-gradient(#00ffff ${pomodoroRingPct}%, rgba(0,255,255,0.12) 0%)`,
              }}
            >
              <div className="fg-ring-core">
                <p className="fg-ring-value">{pomodoroRingPct}%</p>
                <p className="fg-subtle">Focus fill</p>
              </div>
            </div>
          </div>
        </article>

        <article className="fg-card fg-card-goal">
          <header className="fg-card-head">
            <h2>Today Goal</h2>
            <span className="fg-chip">
              {focusedMinutes}/{dailyGoalMinutes} min
            </span>
          </header>
          <div
            className="fg-goal-track"
            role="progressbar"
            aria-valuenow={goalPct}
          >
            <div className="fg-goal-fill" style={{ width: `${goalPct}%` }} />
          </div>
          <div className="fg-kpi-row">
            <div>
              <p className="fg-kpi-label">Focus Time</p>
              <p className="fg-kpi-value">
                {loading
                  ? "..."
                  : summary
                    ? formatSeconds(summary.total_focus_seconds)
                    : "0m"}
              </p>
            </div>
            <div>
              <p className="fg-kpi-label">Sessions</p>
              <p className="fg-kpi-value">
                {loading ? "..." : (summary?.session_count ?? 0)}
              </p>
            </div>
            <div>
              <p className="fg-kpi-label">Distractions</p>
              <p className="fg-kpi-value">
                {loading ? "..." : (summary?.distraction_count ?? 0)}
              </p>
            </div>
          </div>
        </article>

        <article className="fg-card fg-card-events">
          <header className="fg-card-head">
            <h2>Recent AI Events</h2>
            <Link href="/analytics" className="fg-link-inline">
              Analytics
            </Link>
          </header>
          {loading ? (
            <p className="fg-subtle">Loading AI events...</p>
          ) : recentEvents.length === 0 ? (
            <p className="fg-subtle">No recent events.</p>
          ) : (
            <ul className="fg-event-list">
              {recentEvents.map((event) => (
                <li key={event.event_id} className="fg-event-item">
                  <span className="fg-event-time">
                    {formatEventTime(event.start_at)}
                  </span>
                  <span className="fg-event-type">{event.event_type}</span>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="fg-card fg-card-tasks">
          <header className="fg-card-head">
            <h2>Active Tasks</h2>
            <Link href="/tasks" className="fg-link-inline">
              View all
            </Link>
          </header>
          {loading ? (
            <p className="fg-subtle">Loading tasks...</p>
          ) : tasks.length === 0 ? (
            <p className="fg-subtle">No active tasks.</p>
          ) : (
            <ul className="fg-task-list">
              {tasks.slice(0, 4).map((task) => (
                <li key={task.task_id} className="fg-task-item">
                  <div>
                    <p className="fg-task-title">{task.title}</p>
                    <p className="fg-task-meta">
                      {task.subject_name ?? "General"}
                    </p>
                  </div>
                  <span className="fg-chip">{task.status}</span>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>
    </div>
  );
}
