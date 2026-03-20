"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
    <div className="bg-white rounded-lg shadow p-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        {label}
      </p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [enemyStats, setEnemyStats] = useState<EnemyStats | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Link href="/timer">
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors">
            ▶ Start Session
          </button>
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Daily summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <StatCard
          label="Focus Time"
          value={
            loading
              ? "…"
              : summary
                ? formatSeconds(summary.total_focus_seconds)
                : "0m"
          }
        />
        <StatCard
          label="Sessions"
          value={loading ? "…" : (summary?.session_count ?? 0)}
        />
        <StatCard
          label="Distractions"
          value={loading ? "…" : (summary?.distraction_count ?? 0)}
        />
        <StatCard
          label="Fatigue Events"
          value={loading ? "…" : (summary?.fatigue_count ?? 0)}
        />
        <StatCard
          label="Phone Detections"
          value={loading ? "…" : (enemyStats?.phone_detected_count ?? 0)}
        />
      </div>

      <p className="text-xs text-gray-500 mb-6">
        Phone detections/session today:{" "}
        {loading ? "…" : (enemyStats?.phone_per_session ?? 0)}
      </p>

      {/* Active tasks */}
      <div className="bg-white rounded-lg shadow p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-900">Active Tasks</h2>
          <Link href="/tasks" className="text-sm text-blue-600 hover:underline">
            View all →
          </Link>
        </div>
        {loading ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : tasks.length === 0 ? (
          <p className="text-gray-400 text-sm">No active tasks.</p>
        ) : (
          <ul className="divide-y">
            {tasks.map((task) => (
              <li key={task.task_id} className="py-2 flex items-center gap-3">
                <span className="flex-1 text-sm font-medium text-gray-800">
                  {task.title}
                </span>
                {task.subject_name && (
                  <span className="text-xs text-gray-400">
                    {task.subject_name}
                  </span>
                )}
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full capitalize">
                  {task.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-6">
        <EngagementWidget />
      </div>
    </div>
  );
}
