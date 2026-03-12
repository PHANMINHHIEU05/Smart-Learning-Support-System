'use client'

import { useEffect, useReducer, useRef, useState } from 'react'
import { apiFetch } from '@/lib/api-client'
import type {
  BlockCreate,
  BlockType,
  SessionBlock,
  SessionCreate,
  StudySession,
  Task,
  UserSetting,
} from '@/types/api'

// ---------------------------------------------------------------------------
// Timer state machine
// ---------------------------------------------------------------------------

type TimerStatus = 'idle' | 'running' | 'paused' | 'finished'

interface TimerState {
  status: TimerStatus
  secondsLeft: number
  blockType: BlockType
  cycleCount: number // number of focus blocks completed in current session
  session: StudySession | null
  currentBlock: SessionBlock | null
}

type TimerAction =
  | { type: 'START'; session: StudySession; block: SessionBlock; seconds: number }
  | { type: 'TICK' }
  | { type: 'PAUSE' }
  | { type: 'RESUME' }
  | { type: 'NEXT_BLOCK'; block: SessionBlock; seconds: number; blockType: BlockType; cycle: number }
  | { type: 'STOP' }

function timerReducer(state: TimerState, action: TimerAction): TimerState {
  switch (action.type) {
    case 'START':
      return {
        ...state,
        status: 'running',
        secondsLeft: action.seconds,
        blockType: 'focus',
        cycleCount: 0,
        session: action.session,
        currentBlock: action.block,
      }
    case 'TICK':
      if (state.secondsLeft <= 1) return { ...state, status: 'finished', secondsLeft: 0 }
      return { ...state, secondsLeft: state.secondsLeft - 1 }
    case 'PAUSE':
      return { ...state, status: 'paused' }
    case 'RESUME':
      return { ...state, status: 'running' }
    case 'NEXT_BLOCK':
      return {
        ...state,
        status: 'running',
        secondsLeft: action.seconds,
        blockType: action.blockType,
        cycleCount: action.cycle,
        currentBlock: action.block,
      }
    case 'STOP':
      return {
        status: 'idle',
        secondsLeft: 0,
        blockType: 'focus',
        cycleCount: 0,
        session: null,
        currentBlock: null,
      }
    default:
      return state
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const BLOCK_LABEL: Record<BlockType, string> = {
  focus: '🎯 Focus',
  break: '☕ Short Break',
  long_break: '🌿 Long Break',
}

const BLOCK_COLOR: Record<BlockType, string> = {
  focus: 'text-blue-600',
  break: 'text-green-600',
  long_break: 'text-purple-600',
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TimerPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedTaskId, setSelectedTaskId] = useState<string>('')
  const [settings, setSettings] = useState<UserSetting | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)

  const [timer, dispatch] = useReducer(timerReducer, {
    status: 'idle',
    secondsLeft: 0,
    blockType: 'focus',
    cycleCount: 0,
    session: null,
    currentBlock: null,
  })

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Load tasks + settings on mount
  useEffect(() => {
    Promise.all([
      apiFetch<Task[]>('/api/v1/tasks/?status=todo&limit=50'),
      apiFetch<Task[]>('/api/v1/tasks/?status=doing&limit=50'),
      apiFetch<UserSetting>('/api/v1/settings'),
    ])
      .then(([todo, doing, s]) => {
        setTasks([...todo, ...doing])
        setSettings(s)
      })
      .catch((e) => setError(e.message))
  }, [])

  // Countdown tick
  useEffect(() => {
    if (timer.status === 'running') {
      intervalRef.current = setInterval(() => dispatch({ type: 'TICK' }), 1000)
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [timer.status])

  // Auto-advance to next block when finished
  useEffect(() => {
    if (timer.status === 'finished' && timer.session) {
      handleNextBlock()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timer.status])

  const focusSec = (settings?.pomodoro_focus_minutes ?? 25) * 60
  const breakSec = (settings?.pomodoro_break_minutes ?? 5) * 60
  const longBreakSec = (settings?.pomodoro_long_break_minutes ?? 15) * 60
  const cyclesBeforeLong = settings?.pomodoro_cycles_before_long_break ?? 4

  const handleStart = async () => {
    if (!settings) return
    setStarting(true)
    setError(null)
    try {
      const session = await apiFetch<StudySession>('/api/v1/sessions/', {
        method: 'POST',
        body: JSON.stringify({
          planned_mode: 'pomodoro',
          ...(selectedTaskId ? { task_id: selectedTaskId } : {}),
        } satisfies SessionCreate),
      })
      const block = await apiFetch<SessionBlock>('/api/v1/blocks/', {
        method: 'POST',
        body: JSON.stringify({
          session_id: session.session_id,
          block_type: 'focus',
          planned_duration_seconds: focusSec,
        } satisfies BlockCreate),
      })
      dispatch({ type: 'START', session, block, seconds: focusSec })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start session')
    } finally {
      setStarting(false)
    }
  }

  const handleNextBlock = async () => {
    if (!timer.session) return
    const newCycle =
      timer.blockType === 'focus' ? timer.cycleCount + 1 : timer.cycleCount

    let nextType: BlockType
    let nextSec: number
    if (timer.blockType === 'focus') {
      if (newCycle % cyclesBeforeLong === 0) {
        nextType = 'long_break'
        nextSec = longBreakSec
      } else {
        nextType = 'break'
        nextSec = breakSec
      }
    } else {
      nextType = 'focus'
      nextSec = focusSec
    }

    try {
      const block = await apiFetch<SessionBlock>('/api/v1/blocks/', {
        method: 'POST',
        body: JSON.stringify({
          session_id: timer.session.session_id,
          block_type: nextType,
          planned_duration_seconds: nextSec,
        } satisfies BlockCreate),
      })
      dispatch({ type: 'NEXT_BLOCK', block, seconds: nextSec, blockType: nextType, cycle: newCycle })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create next block')
    }
  }

  const handleStop = async () => {
    if (!timer.session) return
    try {
      await apiFetch(`/api/v1/sessions/${timer.session.session_id}/end`, {
        method: 'PATCH',
        body: JSON.stringify({ end_reason: 'stopped' }),
      })
    } catch {
      // best-effort — session has ended client-side regardless
    }
    dispatch({ type: 'STOP' })
  }

  const progressPct = (() => {
    if (timer.status === 'idle') return 0
    const total =
      timer.blockType === 'focus'
        ? focusSec
        : timer.blockType === 'long_break'
          ? longBreakSec
          : breakSec
    return total > 0 ? Math.round(((total - timer.secondsLeft) / total) * 100) : 0
  })()

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-6">Study Timer</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {timer.status === 'idle' ? (
        <div className="bg-white rounded-xl shadow p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Task (optional)
            </label>
            <select
              value={selectedTaskId}
              onChange={(e) => setSelectedTaskId(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— No task selected —</option>
              {tasks.map((t) => (
                <option key={t.task_id} value={t.task_id}>
                  {t.title}
                </option>
              ))}
            </select>
          </div>

          {settings && (
            <div className="text-xs text-gray-500 bg-gray-50 rounded p-3 space-y-1">
              <p>Focus: {settings.pomodoro_focus_minutes} min</p>
              <p>Short break: {settings.pomodoro_break_minutes} min</p>
              <p>Long break: {settings.pomodoro_long_break_minutes} min</p>
              <p>Cycles before long break: {settings.pomodoro_cycles_before_long_break}</p>
            </div>
          )}

          <button
            onClick={handleStart}
            disabled={starting || !settings}
            className="w-full bg-blue-600 text-white rounded-lg py-3 font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {starting ? 'Starting…' : '▶ Start Pomodoro'}
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow p-6 text-center space-y-4">
          <p className={`text-lg font-semibold ${BLOCK_COLOR[timer.blockType]}`}>
            {BLOCK_LABEL[timer.blockType]}
          </p>

          <p className="text-6xl font-mono font-bold text-gray-900">
            {formatTime(timer.secondsLeft)}
          </p>

          {/* Progress bar */}
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          <p className="text-sm text-gray-500">
            Cycle {timer.cycleCount === 0 ? 1 : timer.cycleCount} ·{' '}
            {timer.cycleCount} focus block{timer.cycleCount !== 1 ? 's' : ''} completed
          </p>

          <div className="flex justify-center gap-3">
            {timer.status === 'running' ? (
              <button
                onClick={() => dispatch({ type: 'PAUSE' })}
                className="px-5 py-2 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50"
              >
                ⏸ Pause
              </button>
            ) : (
              <button
                onClick={() => dispatch({ type: 'RESUME' })}
                className="px-5 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
              >
                ▶ Resume
              </button>
            )}
            <button
              onClick={handleStop}
              className="px-5 py-2 rounded-lg border border-red-300 text-red-600 text-sm font-medium hover:bg-red-50"
            >
              ■ Stop
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
