"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import {
  DEFAULT_CRITICAL_EVENT_TYPES,
  MODE_LABELS,
  STATUS_CONFIG,
  normalizeMonitoringStatus,
  pickUnackedCriticalAlerts,
} from "@/lib/monitoring/bridge";
import type {
  AlertResponse,
  BlockCreate,
  BlockType,
  ModeSwitchResponse,
  MonitoringStatusResponse,
  SessionBlock,
  SessionCreate,
  StudySession,
  Task,
  UserSetting,
} from "@/types/api";

// ---------------------------------------------------------------------------
// Timer state machine
// ---------------------------------------------------------------------------

type TimerStatus = "idle" | "running" | "paused" | "finished";

interface TimerState {
  status: TimerStatus;
  secondsLeft: number;
  blockType: BlockType;
  cycleCount: number; // number of focus blocks completed in current session
  session: StudySession | null;
  currentBlock: SessionBlock | null;
}

type TimerAction =
  | {
      type: "START";
      session: StudySession;
      block: SessionBlock;
      seconds: number;
    }
  | { type: "TICK" }
  | { type: "PAUSE" }
  | { type: "RESUME" }
  | {
      type: "NEXT_BLOCK";
      block: SessionBlock;
      seconds: number;
      blockType: BlockType;
      cycle: number;
    }
  | { type: "STOP" };

function timerReducer(state: TimerState, action: TimerAction): TimerState {
  switch (action.type) {
    case "START":
      return {
        ...state,
        status: "running",
        secondsLeft: action.seconds,
        blockType: "focus",
        cycleCount: 0,
        session: action.session,
        currentBlock: action.block,
      };
    case "TICK":
      if (state.secondsLeft <= 1)
        return { ...state, status: "finished", secondsLeft: 0 };
      return { ...state, secondsLeft: state.secondsLeft - 1 };
    case "PAUSE":
      return { ...state, status: "paused" };
    case "RESUME":
      return { ...state, status: "running" };
    case "NEXT_BLOCK":
      return {
        ...state,
        status: "running",
        secondsLeft: action.seconds,
        blockType: action.blockType,
        cycleCount: action.cycle,
        currentBlock: action.block,
      };
    case "STOP":
      return {
        status: "idle",
        secondsLeft: 0,
        blockType: "focus",
        cycleCount: 0,
        session: null,
        currentBlock: null,
      };
    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

const BLOCK_LABEL: Record<BlockType, string> = {
  focus: "🎯 Focus",
  break: "☕ Short Break",
  long_break: "🌿 Long Break",
};

const BLOCK_COLOR: Record<BlockType, string> = {
  focus: "text-blue-600",
  break: "text-green-600",
  long_break: "text-purple-600",
};

const MONITORING_MODES = [
  "external_camera",
  "in_web_widget",
  "alerts_only",
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TimerPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string>("");
  const [settings, setSettings] = useState<UserSetting | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [switchingMode, setSwitchingMode] = useState(false);
  const [savingSoundPref, setSavingSoundPref] = useState(false);

  // Monitoring state
  const [monitoringStatus, setMonitoringStatus] =
    useState<MonitoringStatusResponse | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<AlertResponse[]>([]);
  const [ackedAlertIds, setAckedAlertIds] = useState<Set<string>>(new Set());
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const previousCriticalCountRef = useRef(0);

  const [timer, dispatch] = useReducer(timerReducer, {
    status: "idle",
    secondsLeft: 0,
    blockType: "focus",
    cycleCount: 0,
    session: null,
    currentBlock: null,
  });

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Monitoring polling ────────────────────────────────────────────────────
  const pollMonitoring = useCallback(async (sessionId: string) => {
    try {
      const [status, alerts] = await Promise.all([
        apiFetch<MonitoringStatusResponse>("/api/v1/monitoring/status"),
        apiFetch<AlertResponse[]>(
          `/api/v1/alerts/?session_id=${sessionId}&limit=20`,
        ),
      ]);
      setMonitoringStatus(status);
      setRecentAlerts(alerts);
    } catch {
      // ignore transient poll errors — show last known state
    }
  }, []);

  useEffect(() => {
    const sessionId = timer.session?.session_id;
    if (timer.status !== "idle" && sessionId) {
      // immediate first poll then every 6 s
      void pollMonitoring(sessionId);
      pollingRef.current = setInterval(
        () => void pollMonitoring(sessionId),
        6000,
      );
    } else {
      if (pollingRef.current) clearInterval(pollingRef.current);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [timer.status, timer.session?.session_id, pollMonitoring]);

  // Derived: unacked critical alerts
  const normalizedStatus = normalizeMonitoringStatus(monitoringStatus);
  const criticalEventTypes =
    normalizedStatus.severityDefaults.critical ?? DEFAULT_CRITICAL_EVENT_TYPES;
  const unackedCriticalAlerts = pickUnackedCriticalAlerts(
    recentAlerts,
    ackedAlertIds,
    criticalEventTypes,
  );

  const selectedMode =
    normalizedStatus.activeMode ??
    settings?.monitoring_mode ??
    "external_camera";
  const criticalSoundEnabled = settings?.critical_sound_enabled ?? true;

  // Play a short browser beep when new critical alerts arrive (if enabled).
  useEffect(() => {
    const currentCount = unackedCriticalAlerts.length;
    const increased = currentCount > previousCriticalCountRef.current;
    previousCriticalCountRef.current = currentCount;

    if (!increased || !criticalSoundEnabled) return;

    try {
      const audioCtx = new window.AudioContext();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.value = 880;
      gain.gain.value = 0.05;
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      setTimeout(() => {
        osc.stop();
        void audioCtx.close();
      }, 180);
    } catch {
      // Ignore browsers that block autoplayed audio.
    }
  }, [unackedCriticalAlerts.length, criticalSoundEnabled]);

  // Load tasks + settings on mount
  useEffect(() => {
    Promise.all([
      apiFetch<Task[]>("/api/v1/tasks/?status=todo&limit=50"),
      apiFetch<Task[]>("/api/v1/tasks/?status=doing&limit=50"),
      apiFetch<UserSetting>("/api/v1/settings/"),
    ])
      .then(([todo, doing, s]) => {
        setTasks([...todo, ...doing]);
        setSettings(s);
      })
      .catch((e) => setError(e.message));
  }, []);

  // Countdown tick
  useEffect(() => {
    if (timer.status === "running") {
      intervalRef.current = setInterval(() => dispatch({ type: "TICK" }), 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [timer.status]);

  // Auto-advance to next block when finished
  useEffect(() => {
    if (timer.status === "finished" && timer.session) {
      handleNextBlock();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timer.status]);

  const focusSec = (settings?.pomodoro_focus_minutes ?? 25) * 60;
  const breakSec = (settings?.pomodoro_break_minutes ?? 5) * 60;
  const longBreakSec = (settings?.pomodoro_long_break_minutes ?? 15) * 60;
  const cyclesBeforeLong = settings?.pomodoro_cycles_before_long_break ?? 4;

  const handleStart = async () => {
    if (!settings) return;
    setStarting(true);
    setError(null);
    setAckedAlertIds(new Set());
    try {
      const session = await apiFetch<StudySession>("/api/v1/sessions/", {
        method: "POST",
        body: JSON.stringify({
          planned_mode: "pomodoro",
          started_at: new Date().toISOString(),
          ...(selectedTaskId ? { task_id: selectedTaskId } : {}),
        } satisfies SessionCreate),
      });
      const block = await apiFetch<SessionBlock>("/api/v1/blocks/", {
        method: "POST",
        body: JSON.stringify({
          session_id: session.session_id,
          block_type: "focus",
          start_at: new Date().toISOString(),
          planned_duration_seconds: focusSec,
        } satisfies BlockCreate),
      });
      dispatch({ type: "START", session, block, seconds: focusSec });

      // Bật giám sát AI nếu được bật trong settings
      if (settings.ai_monitoring_enabled !== false) {
        try {
          const status = await apiFetch<MonitoringStatusResponse>(
            "/api/v1/monitoring/start",
            {
              method: "POST",
              body: JSON.stringify({
                session_id: session.session_id,
                show_display: true,
              }),
            },
          );
          setMonitoringStatus(status);
        } catch (monitoringError: unknown) {
          setMonitoringStatus(null);
          setError(
            monitoringError instanceof Error
              ? `Monitoring failed to start: ${monitoringError.message}`
              : "Monitoring failed to start",
          );
        }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setStarting(false);
    }
  };

  const handleNextBlock = async () => {
    if (!timer.session) return;
    const newCycle =
      timer.blockType === "focus" ? timer.cycleCount + 1 : timer.cycleCount;

    let nextType: BlockType;
    let nextSec: number;
    if (timer.blockType === "focus") {
      if (newCycle % cyclesBeforeLong === 0) {
        nextType = "long_break";
        nextSec = longBreakSec;
      } else {
        nextType = "break";
        nextSec = breakSec;
      }
    } else {
      nextType = "focus";
      nextSec = focusSec;
    }

    try {
      const block = await apiFetch<SessionBlock>("/api/v1/blocks/", {
        method: "POST",
        body: JSON.stringify({
          session_id: timer.session.session_id,
          block_type: nextType,
          start_at: new Date().toISOString(),
          planned_duration_seconds: nextSec,
        } satisfies BlockCreate),
      });
      dispatch({
        type: "NEXT_BLOCK",
        block,
        seconds: nextSec,
        blockType: nextType,
        cycle: newCycle,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create next block");
    }
  };

  const handleStop = async () => {
    if (!timer.session) return;
    try {
      await apiFetch(`/api/v1/sessions/${timer.session.session_id}/end`, {
        method: "PATCH",
        body: JSON.stringify({
          ended_at: new Date().toISOString(),
          end_reason: "stopped",
        }),
      });
    } catch {
      // best-effort — session has ended client-side regardless
    }
    // Dừng giám sát AI nếu đang chạy
    if (
      normalizedStatus.status === "active" ||
      normalizedStatus.status === "degraded"
    ) {
      apiFetch("/api/v1/monitoring/stop", { method: "POST" }).catch(() => {});
    }
    setMonitoringStatus(null);
    setRecentAlerts([]);
    dispatch({ type: "STOP" });
  };

  const handleRetryMonitoring = async () => {
    if (!timer.session) return;
    try {
      const status = await apiFetch<MonitoringStatusResponse>(
        "/api/v1/monitoring/start",
        {
          method: "POST",
          body: JSON.stringify({
            session_id: timer.session.session_id,
            show_display: true,
          }),
        },
      );
      setMonitoringStatus(status);
    } catch {
      // keep degraded banner visible
    }
  };

  const handleSwitchMode = async (mode: string) => {
    setSwitchingMode(true);
    setError(null);
    try {
      const res = await apiFetch<ModeSwitchResponse>(
        "/api/v1/monitoring/mode",
        {
          method: "POST",
          body: JSON.stringify({ mode }),
        },
      );

      setMonitoringStatus((prev) =>
        prev
          ? {
              ...prev,
              status: res.status,
              active_mode: res.applied_mode,
              degraded_reason: res.degraded_reason,
            }
          : {
              status: res.status,
              active_mode: res.applied_mode,
              pid: null,
              degraded_reason: res.degraded_reason,
              severity_defaults: {
                critical: DEFAULT_CRITICAL_EVENT_TYPES,
                medium: [],
                soft: [],
              },
            },
      );

      const updatedSettings = await apiFetch<UserSetting>("/api/v1/settings/", {
        method: "PUT",
        body: JSON.stringify({ monitoring_mode: res.applied_mode }),
      });
      setSettings(updatedSettings);
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to switch monitoring mode",
      );
    } finally {
      setSwitchingMode(false);
    }
  };

  const handleToggleCriticalSound = async (enabled: boolean) => {
    setSavingSoundPref(true);
    setError(null);
    try {
      const updatedSettings = await apiFetch<UserSetting>("/api/v1/settings/", {
        method: "PUT",
        body: JSON.stringify({ critical_sound_enabled: enabled }),
      });
      setSettings(updatedSettings);
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to save sound preference",
      );
    } finally {
      setSavingSoundPref(false);
    }
  };

  const handleAckAlert = (alertId: string) => {
    setAckedAlertIds((prev) => new Set(prev).add(alertId));
    apiFetch(`/api/v1/monitoring/alerts/${alertId}/ack`, {
      method: "POST",
    }).catch(() => {});
  };

  const handleAckAll = () => {
    unackedCriticalAlerts.forEach((a) => handleAckAlert(String(a.alert_id)));
  };

  const progressPct = (() => {
    if (timer.status === "idle") return 0;
    const total =
      timer.blockType === "focus"
        ? focusSec
        : timer.blockType === "long_break"
          ? longBreakSec
          : breakSec;
    return total > 0
      ? Math.round(((total - timer.secondsLeft) / total) * 100)
      : 0;
  })();

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-6">Study Timer</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {timer.status === "idle" ? (
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
              <p>
                Cycles before long break:{" "}
                {settings.pomodoro_cycles_before_long_break}
              </p>
              {settings.ai_monitoring_enabled !== false && (
                <p className="text-blue-600">
                  AI monitoring:{" "}
                  {MODE_LABELS[settings.monitoring_mode ?? "external_camera"] ??
                    "External camera"}
                </p>
              )}
            </div>
          )}

          <button
            onClick={handleStart}
            disabled={starting || !settings}
            className="w-full bg-blue-600 text-white rounded-lg py-3 font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {starting ? "Starting…" : "▶ Start Pomodoro"}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {/* ── Critical alert bar ── */}
          {unackedCriticalAlerts.length > 0 && (
            <div className="rounded-xl bg-red-50 border border-red-300 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-red-700">
                  ⚠ Critical Alert
                  {unackedCriticalAlerts.length > 1 &&
                    ` (${unackedCriticalAlerts.length})`}
                </span>
                <button
                  onClick={handleAckAll}
                  className="text-xs text-red-600 underline hover:text-red-800"
                >
                  Dismiss all
                </button>
              </div>
              <p className="text-sm text-red-700">
                {unackedCriticalAlerts[0].message ??
                  "High-severity event detected"}
              </p>
              {unackedCriticalAlerts.length === 1 && (
                <button
                  onClick={() =>
                    handleAckAlert(String(unackedCriticalAlerts[0].alert_id))
                  }
                  className="text-xs text-red-600 underline hover:text-red-800"
                >
                  Dismiss
                </button>
              )}
            </div>
          )}

          {/* ── Main timer card ── */}
          <div className="bg-white rounded-xl shadow p-6 text-center space-y-4">
            <p
              className={`text-lg font-semibold ${BLOCK_COLOR[timer.blockType]}`}
            >
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
              Cycle {timer.cycleCount === 0 ? 1 : timer.cycleCount} ·{" "}
              {timer.cycleCount} focus block{timer.cycleCount !== 1 ? "s" : ""}{" "}
              completed
            </p>

            <div className="flex justify-center gap-3">
              {timer.status === "running" ? (
                <button
                  onClick={() => dispatch({ type: "PAUSE" })}
                  className="px-5 py-2 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50"
                >
                  ⏸ Pause
                </button>
              ) : (
                <button
                  onClick={() => dispatch({ type: "RESUME" })}
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

          {/* ── Monitoring widget ── */}
          {settings?.ai_monitoring_enabled !== false && (
            <div className="bg-white rounded-xl shadow p-4 space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-700">AI Monitoring</span>
                {(() => {
                  const cfg = STATUS_CONFIG[normalizedStatus.status ?? "idle"];
                  return (
                    <span
                      className={`flex items-center gap-1.5 ${cfg.labelClass}`}
                    >
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${cfg.dot}`}
                      />
                      {cfg.label}
                    </span>
                  );
                })()}
              </div>
              {normalizedStatus.activeMode && (
                <p className="text-xs text-gray-500">
                  Mode:{" "}
                  {MODE_LABELS[normalizedStatus.activeMode] ??
                    normalizedStatus.activeMode}
                </p>
              )}
              <div className="grid grid-cols-1 gap-2 pt-1">
                <label className="text-xs text-gray-600">Monitoring mode</label>
                <select
                  value={selectedMode}
                  onChange={(e) => void handleSwitchMode(e.target.value)}
                  disabled={switchingMode}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                >
                  {MONITORING_MODES.map((mode) => (
                    <option key={mode} value={mode}>
                      {MODE_LABELS[mode]}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center justify-between border border-gray-200 rounded px-2 py-1.5">
                <span className="text-xs text-gray-600">
                  Critical alert sound
                </span>
                <input
                  type="checkbox"
                  checked={criticalSoundEnabled}
                  disabled={savingSoundPref}
                  onChange={(e) =>
                    void handleToggleCriticalSound(e.target.checked)
                  }
                  className="w-4 h-4 text-blue-600 rounded"
                />
              </label>
              {normalizedStatus.status === "degraded" &&
                normalizedStatus.degradedReason && (
                  <div className="rounded-lg bg-amber-50 border border-amber-200 p-2 text-xs text-amber-800 space-y-1">
                    <p>{normalizedStatus.degradedReason.message}</p>
                    <p className="text-amber-600">
                      Fallback:{" "}
                      {MODE_LABELS[
                        normalizedStatus.degradedReason.fallback_mode
                      ] ?? normalizedStatus.degradedReason.fallback_mode}
                    </p>
                    {normalizedStatus.degradedReason.recoverable && (
                      <button
                        onClick={handleRetryMonitoring}
                        className="text-amber-700 underline hover:text-amber-900"
                      >
                        Retry monitoring
                      </button>
                    )}
                  </div>
                )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
