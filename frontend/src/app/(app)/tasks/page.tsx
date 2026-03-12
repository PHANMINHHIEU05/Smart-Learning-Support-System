'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api-client'
import type { Task, TaskCreate, TaskStatus, TaskUpdate } from '@/types/api'

const STATUS_TABS: TaskStatus[] = ['todo', 'doing', 'done', 'archived']

const STATUS_COLORS: Record<TaskStatus, string> = {
  todo: 'bg-gray-100 text-gray-700',
  doing: 'bg-blue-100 text-blue-700',
  done: 'bg-green-100 text-green-700',
  archived: 'bg-yellow-100 text-yellow-700',
}

const PRIORITY_LABELS: Record<number, string> = {
  1: 'Very Low',
  2: 'Low',
  3: 'Normal',
  4: 'High',
  5: 'Urgent',
}

const EMPTY_FORM: TaskCreate = {
  title: '',
  description: '',
  priority: 3,
  subject_name: '',
  estimated_minutes: undefined,
  due_at: undefined,
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [activeTab, setActiveTab] = useState<TaskStatus>('todo')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState<TaskCreate>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const fetchTasks = (status: TaskStatus) => {
    setLoading(true)
    setError(null)
    apiFetch<Task[]>(`/api/v1/tasks/?status=${status}&limit=50`)
      .then(setTasks)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchTasks(activeTab)
  }, [activeTab])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload: TaskCreate = {
        title: formData.title,
        ...(formData.description ? { description: formData.description } : {}),
        priority: formData.priority,
        ...(formData.subject_name ? { subject_name: formData.subject_name } : {}),
        ...(formData.estimated_minutes ? { estimated_minutes: formData.estimated_minutes } : {}),
        ...(formData.due_at ? { due_at: new Date(formData.due_at).toISOString() } : {}),
      }
      await apiFetch<Task>('/api/v1/tasks/', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setShowModal(false)
      setFormData(EMPTY_FORM)
      fetchTasks(activeTab)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create task')
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (task: Task, newStatus: TaskStatus) => {
    try {
      await apiFetch<Task>(`/api/v1/tasks/${task.task_id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus } satisfies TaskUpdate),
      })
      fetchTasks(activeTab)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to update task')
    }
  }

  const handleDelete = async (task: Task) => {
    if (!confirm(`Delete "${task.title}"?`)) return
    try {
      await apiFetch(`/api/v1/tasks/${task.task_id}`, { method: 'DELETE' })
      setTasks((prev) => prev.filter((t) => t.task_id !== task.task_id))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to delete task')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Tasks</h1>
        <button
          onClick={() => { setFormData(EMPTY_FORM); setShowModal(true) }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          + New Task
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Status tabs */}
      <div className="flex gap-2 mb-4 border-b">
        {STATUS_TABS.map((s) => (
          <button
            key={s}
            onClick={() => setActiveTab(s)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              activeTab === s
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Task list */}
      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : tasks.length === 0 ? (
        <p className="text-gray-400 text-sm">No {activeTab} tasks.</p>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <div key={task.task_id} className="bg-white rounded-lg shadow px-4 py-3 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{task.title}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  {task.subject_name && (
                    <span className="text-xs text-gray-400">{task.subject_name}</span>
                  )}
                  <span className="text-xs text-gray-400">
                    P{task.priority} — {PRIORITY_LABELS[task.priority] ?? ''}
                  </span>
                  {task.due_at && (
                    <span className="text-xs text-orange-500">
                      due {new Date(task.due_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>

              {/* Status badge + selector */}
              <select
                value={task.status}
                onChange={(e) => handleStatusChange(task, e.target.value as TaskStatus)}
                className={`text-xs px-2 py-1 rounded-full border-0 font-medium cursor-pointer ${STATUS_COLORS[task.status]}`}
              >
                {STATUS_TABS.map((s) => (
                  <option key={s} value={s} className="bg-white text-gray-800">
                    {s}
                  </option>
                ))}
              </select>

              <button
                onClick={() => handleDelete(task)}
                className="text-red-400 hover:text-red-600 text-sm px-2"
                aria-label="Delete task"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold mb-4">New Task</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData((f) => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData((f) => ({ ...f, description: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={2}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                  <input
                    type="text"
                    value={formData.subject_name}
                    onChange={(e) => setFormData((f) => ({ ...f, subject_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select
                    value={formData.priority}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, priority: Number(e.target.value) }))
                    }
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {[1, 2, 3, 4, 5].map((p) => (
                      <option key={p} value={p}>
                        {p} — {PRIORITY_LABELS[p]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Est. minutes
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={formData.estimated_minutes ?? ''}
                    onChange={(e) =>
                      setFormData((f) => ({
                        ...f,
                        estimated_minutes: e.target.value ? Number(e.target.value) : undefined,
                      }))
                    }
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Due date</label>
                  <input
                    type="date"
                    value={formData.due_at ?? ''}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, due_at: e.target.value || undefined }))
                    }
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-sm rounded bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving…' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
