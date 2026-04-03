"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api-client";
import { EngagementWidget } from "@/components/EngagementWidget";
import type { DailySummary, EnemyStats, Task } from "@/types/api";

function formatSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

interface StatCardProps {
  label: string;
  value: string | number;
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="metric-tile stagger-item">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [enemyStats, setEnemyStats] = useState<EnemyStats | null>(null);
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
      apiFetch<Task[]>("/api/v1/tasks/?status=todo&limit=5"),
    ])
      .then(([sum, enemies, taskList]) => {
        setSummary(sum);
        setEnemyStats(enemies);
        setTasks(taskList ?? []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="app-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">
            Overview of focus, distractions, and active work.
          </p>
        </div>
        <Link
          href="/timer"
          prefetch
          onMouseEnter={() => router.prefetch("/timer")}
          onFocus={() => router.prefetch("/timer")}
          className="btn-primary"
        >
          Start Session
        </Link>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5 md:gap-4">
        <StatCard
          label="Focus Time"
          value={
            loading
              ? "..."
              : summary
                ? formatSeconds(summary.total_focus_seconds)
                : "0m"
          }
        />
        <StatCard
          label="Sessions"
          value={loading ? "..." : (summary?.session_count ?? 0)}
        />
        <StatCard
          label="Distractions"
          value={loading ? "..." : (summary?.distraction_count ?? 0)}
        />
        <StatCard
          label="Fatigue Events"
          value={loading ? "..." : (summary?.fatigue_count ?? 0)}
        />
        <StatCard
          label="Phone Detections"
          value={loading ? "..." : (enemyStats?.phone_detected_count ?? 0)}
        />
      </div>

      <p className="ui-pill w-fit">
        Phone detections per session today:{" "}
        {loading ? "..." : (enemyStats?.phone_per_session ?? 0)}
      </p>

      <div className="surface-card p-5 md:p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-xl font-bold text-slate-900">Active Tasks</h2>
          <Link
            href="/tasks"
            className="text-sm font-semibold text-cyan-700 hover:text-cyan-800"
          >
            View all
          </Link>
        </div>
        {loading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : tasks.length === 0 ? (
          <p className="text-sm text-slate-500">No active tasks.</p>
        ) : (
          <ul className="space-y-2">
            {tasks.map((task) => (
              <li
                key={task.task_id}
                className="rounded-xl border border-slate-200/80 bg-white/75 px-4 py-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {task.title}
                    </p>
                    {task.subject_name && (
                      <p className="mt-1 text-xs text-slate-500">
                        {task.subject_name}
                      </p>
                    )}
                  </div>
                  <span className="ui-pill capitalize">{task.status}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <EngagementWidget />
    </div>
  );
}
