'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api-client'
import type { DailySummary } from '@/types/api'

function formatSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function toISODate(date: Date): string {
  return date.toISOString().split('T')[0]
}

// Build last 7 days (Mon–Sun relative to today) for the bar chart
function last7Days(): string[] {
  const days: string[] = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    days.push(toISODate(d))
  }
  return days
}

export default function AnalyticsPage() {
  const [selectedDate, setSelectedDate] = useState<string>(toISODate(new Date()))
  const [summary, setSummary] = useState<DailySummary | null>(null)
  const [weekData, setWeekData] = useState<Record<string, DailySummary>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch single-day summary whenever selectedDate changes
  useEffect(() => {
    setLoading(true)
    setError(null)
    apiFetch<DailySummary>(`/api/v1/analytics/daily-summary?target_date=${selectedDate}`)
      .then(setSummary)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedDate])

  // Fetch the last 7 days for the bar chart (fire-and-forget)
  useEffect(() => {
    const days = last7Days()
    Promise.allSettled(
      days.map((d) => apiFetch<DailySummary>(`/api/v1/analytics/daily-summary?target_date=${d}`)),
    ).then((results) => {
      const map: Record<string, DailySummary> = {}
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') map[days[i]] = r.value
      })
      setWeekData(map)
    })
  }, [])

  const days = last7Days()
  const maxFocusSec = Math.max(1, ...days.map((d) => weekData[d]?.total_focus_seconds ?? 0))

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

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Daily summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          {
            label: 'Focus Time',
            value: loading ? '…' : summary ? formatSeconds(summary.total_focus_seconds) : '0m',
          },
          { label: 'Sessions', value: loading ? '…' : summary?.session_count ?? 0 },
          { label: 'Distractions', value: loading ? '…' : summary?.distraction_count ?? 0 },
          { label: 'Fatigue Events', value: loading ? '…' : summary?.fatigue_count ?? 0 },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-lg shadow p-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          </div>
        ))}
      </div>

      {/* 7-day bar chart */}
      <div className="bg-white rounded-lg shadow p-5">
        <h2 className="font-semibold text-gray-800 mb-4">Focus Time — Last 7 Days</h2>
        <div className="flex items-end gap-2 h-32">
          {days.map((day) => {
            const data = weekData[day]
            const sec = data?.total_focus_seconds ?? 0
            const pct = Math.round((sec / maxFocusSec) * 100)
            const label = new Date(day + 'T00:00:00').toLocaleDateString(undefined, {
              weekday: 'short',
            })
            const isSelected = day === selectedDate
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
                      isSelected ? 'bg-blue-500' : 'bg-blue-200 group-hover:bg-blue-400'
                    }`}
                    style={{ height: `${Math.max(pct, 2)}%` }}
                  />
                </div>
                <span
                  className={`text-xs font-medium ${
                    isSelected ? 'text-blue-600' : 'text-gray-500'
                  }`}
                >
                  {label}
                </span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
