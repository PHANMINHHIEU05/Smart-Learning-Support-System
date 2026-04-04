"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api-client";
import type { Task, TaskCreate, TaskStatus, TaskUpdate } from "@/types/api";

const STATUS_TABS: TaskStatus[] = ["todo", "doing", "done", "archived"];

const STATUS_COLORS: Record<TaskStatus, string> = {
  todo: "bg-slate-100 text-slate-700",
  doing: "bg-cyan-100 text-cyan-800",
  done: "bg-emerald-100 text-emerald-800",
  archived: "bg-amber-100 text-amber-800",
};

const PRIORITY_LABELS: Record<number, string> = {
  1: "Very Low",
  2: "Low",
  3: "Normal",
  4: "High",
  5: "Urgent",
};

const EMPTY_FORM: TaskCreate = {
  title: "",
  description: "",
  priority: 3,
  subject_name: "",
  estimated_minutes: undefined,
  due_at: undefined,
};

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeTab, setActiveTab] = useState<TaskStatus>("todo");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState<TaskCreate>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const fetchTasks = (status: TaskStatus) => {
    setLoading(true);
    setError(null);
    apiFetch<Task[]>(`/api/v1/tasks/?status=${status}&limit=50`)
      .then(setTasks)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    router.prefetch("/timer");
  }, [router]);

  useEffect(() => {
    fetchTasks(activeTab);
  }, [activeTab]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload: TaskCreate = {
        title: formData.title,
        ...(formData.description ? { description: formData.description } : {}),
        priority: formData.priority,
        ...(formData.subject_name
          ? { subject_name: formData.subject_name }
          : {}),
        ...(formData.estimated_minutes
          ? { estimated_minutes: formData.estimated_minutes }
          : {}),
        ...(formData.due_at
          ? { due_at: new Date(formData.due_at).toISOString() }
          : {}),
      };
      await apiFetch<Task>("/api/v1/tasks/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setShowModal(false);
      setFormData(EMPTY_FORM);
      fetchTasks(activeTab);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create task");
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (task: Task, newStatus: TaskStatus) => {
    try {
      await apiFetch<Task>(`/api/v1/tasks/${task.task_id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus } satisfies TaskUpdate),
      });
      fetchTasks(activeTab);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update task");
    }
  };

  const handleDelete = async (task: Task) => {
    if (!confirm(`Delete "${task.title}"?`)) return;
    try {
      await apiFetch(`/api/v1/tasks/${task.task_id}`, { method: "DELETE" });
      setTasks((prev) => prev.filter((t) => t.task_id !== task.task_id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete task");
    }
  };

  return (
    <div className="app-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Tasks</h1>
          <p className="page-subtitle">
            Manage priorities and keep focus goals visible.
          </p>
        </div>
        <button
          onClick={() => {
            setFormData(EMPTY_FORM);
            setShowModal(true);
          }}
          className="btn-primary"
        >
          New Task
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="surface-card p-4">
        <div className="mb-4 flex flex-wrap gap-2">
          {STATUS_TABS.map((status) => (
            <button
              key={status}
              onClick={() => setActiveTab(status)}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.08em] ${
                activeTab === status
                  ? "border-cyan-500 bg-cyan-600 text-white shadow-md shadow-cyan-600/25"
                  : "border-slate-200 bg-white/80 text-slate-600 hover:border-cyan-300 hover:text-cyan-700"
              }`}
            >
              {status}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : tasks.length === 0 ? (
          <p className="text-sm text-slate-500">No {activeTab} tasks.</p>
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => (
              <div
                key={task.task_id}
                className="rounded-xl border border-slate-200/80 bg-white/75 px-4 py-3"
              >
                <div className="flex flex-wrap items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-900">
                      {task.title}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      {task.subject_name && (
                        <span className="text-xs text-slate-500">
                          {task.subject_name}
                        </span>
                      )}
                      <span className="text-xs text-slate-500">
                        P{task.priority} -{" "}
                        {PRIORITY_LABELS[task.priority] ?? ""}
                      </span>
                      {task.due_at && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
                          due {new Date(task.due_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>

                  <select
                    value={task.status}
                    onChange={(e) =>
                      handleStatusChange(task, e.target.value as TaskStatus)
                    }
                    className={`rounded-full border-0 px-2 py-1 text-xs font-semibold ${STATUS_COLORS[task.status]}`}
                  >
                    {STATUS_TABS.map((status) => (
                      <option
                        key={status}
                        value={status}
                        className="bg-white text-slate-800"
                      >
                        {status}
                      </option>
                    ))}
                  </select>

                  <button
                    onClick={() => handleDelete(task)}
                    className="rounded-lg border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                    aria-label="Delete task"
                  >
                    Delete
                  </button>
                  <Link
                    href={`/timer?taskId=${task.task_id}`}
                    prefetch
                    onMouseEnter={() => router.prefetch("/timer")}
                    onFocus={() => router.prefetch("/timer")}
                    className="rounded-lg border border-cyan-200 bg-cyan-50 px-2 py-1 text-xs font-semibold text-cyan-700 hover:bg-cyan-100"
                  >
                    Hoc ngay
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 px-4 backdrop-blur-sm">
          <div className="surface-card surface-card-strong w-full max-w-xl p-6 md:p-7">
            <h2 className="text-2xl font-bold text-slate-900">New Task</h2>
            <p className="mt-1 text-sm text-slate-500">
              Add a precise, actionable task to keep sessions focused.
            </p>

            <form onSubmit={handleCreate} className="mt-6 space-y-4">
              <div>
                <label className="field-label">
                  Title <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) =>
                    setFormData((f) => ({ ...f, title: e.target.value }))
                  }
                  className="field-input"
                />
              </div>
              <div>
                <label className="field-label">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) =>
                    setFormData((f) => ({ ...f, description: e.target.value }))
                  }
                  className="field-textarea"
                  rows={3}
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="field-label">Subject</label>
                  <input
                    type="text"
                    value={formData.subject_name}
                    onChange={(e) =>
                      setFormData((f) => ({
                        ...f,
                        subject_name: e.target.value,
                      }))
                    }
                    className="field-input"
                  />
                </div>
                <div>
                  <label className="field-label">Priority</label>
                  <select
                    value={formData.priority}
                    onChange={(e) =>
                      setFormData((f) => ({
                        ...f,
                        priority: Number(e.target.value),
                      }))
                    }
                    className="field-select"
                  >
                    {[1, 2, 3, 4, 5].map((priority) => (
                      <option key={priority} value={priority}>
                        {priority} - {PRIORITY_LABELS[priority]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="field-label">⏱️ Estimated Time</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min={1}
                      max={480}
                      value={formData.estimated_minutes ?? ""}
                      onChange={(e) =>
                        setFormData((f) => ({
                          ...f,
                          estimated_minutes: e.target.value
                            ? Number(e.target.value)
                            : undefined,
                        }))
                      }
                      placeholder="30, 60, 120..."
                      className="field-input flex-1"
                    />
                    <span className="flex items-center text-xs text-slate-500 font-medium">
                      min
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {[15, 30, 45, 60, 90, 120].map((mins) => (
                      <button
                        key={mins}
                        type="button"
                        onClick={() =>
                          setFormData((f) => ({
                            ...f,
                            estimated_minutes: mins,
                          }))
                        }
                        className={`rounded px-2 py-1 text-xs font-medium transition ${
                          formData.estimated_minutes === mins
                            ? "bg-cyan-500 text-white"
                            : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                        }`}
                      >
                        {mins}m
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="field-label">Due Date</label>
                  <input
                    type="date"
                    value={formData.due_at ?? ""}
                    onChange={(e) =>
                      setFormData((f) => ({
                        ...f,
                        due_at: e.target.value || undefined,
                      }))
                    }
                    className="field-input"
                  />
                </div>
              </div>

              <div className="flex flex-wrap justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn-soft"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="btn-primary disabled:opacity-60"
                >
                  {saving ? "Saving..." : "Create Task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
