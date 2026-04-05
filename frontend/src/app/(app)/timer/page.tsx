"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api-client";
import { BreakOverlay202020 } from "@/components/BreakOverlay202020";
import type { CameraStreamMetrics } from "@/components/CameraWidget";
import {
  DEFAULT_CRITICAL_EVENT_TYPES,
  MODE_LABELS,
  STATUS_CONFIG,
  normalizeMonitoringStatus,
  pickUnackedCriticalAlerts,
} from "@/lib/monitoring/bridge";
import type {
  AiEventResponse,
  AlertResponse,
  BlockCreate,
  BlockType,
  InterventionStateResponse,
  ModeSwitchResponse,
  MonitoringStatusResponse,
  SessionBlock,
  SessionCreate,
  StudySession,
  Task,
  UserSetting,
} from "@/types/api";

const CameraWidget = dynamic(
  () => import("@/components/CameraWidget").then((m) => m.CameraWidget),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-xl border border-slate-200 bg-slate-100 p-3 text-xs text-slate-500">
        Initializing camera widget...
      </div>
    ),
  },
);

const WhiteNoiseControl = dynamic(
  () =>
    import("@/components/WhiteNoiseControl").then((m) => m.WhiteNoiseControl),
  {
    ssr: false,
    loading: () => (
      <div className="surface-card p-4 text-xs text-slate-500">
        Loading white noise controls...
      </div>
    ),
  },
);

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
        blockType: action.block.block_type,
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
  focus: "text-cyan-700",
  break: "text-emerald-700",
  long_break: "text-amber-700",
};

const MONITORING_MODES = ["browser_camera", "alerts_only"] as const;

const ERGONOMIC_EVENT_TYPES = [
  "posture_deviation",
  "head_slump",
  "posture_slouch",
  "posture_too_close",
  "near_screen",
  "too_close",
  "face_too_close",
];
const PHONE_EVENT_TYPES = ["phone_detected", "DISTRACTION_PHONE"];

const ERGONOMIC_REMINDER_COOLDOWN_MS = 60000;
const ERGONOMIC_ACTIVE_WINDOW_MS = 30000;
const EYE_REST_CADENCE_SEC = 20 * 60;
const EYE_REST_OVERLAY_SEC = 20;
const SESSION_STORAGE_KEY = "active_study_session_id";
const BLOCK_STORAGE_KEY = "active_study_block_id";
const HEARTBEAT_INTERVAL_MS = 30_000;

function normalizeMonitoringMode(mode: string | null | undefined): string {
  if (mode === "alerts_only") return "alerts_only";
  if (mode === "in_web_widget" || mode === "external_camera") {
    return "browser_camera";
  }
  return mode ?? "browser_camera";
}

function shouldShowExternalDisplay(mode: string): boolean {
  return mode === "external_camera";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TimerPage() {
  const searchParams = useSearchParams();
  const queryTaskId = searchParams.get("taskId") ?? "";
  const [step, setStep] = useState<"idle" | "calibrating" | "studying">("idle");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string>("");
  const [settings, setSettings] = useState<UserSetting | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [startupCalibrationMessage, setStartupCalibrationMessage] = useState<
    string | null
  >(null);
  const [starting, setStarting] = useState(false);
  const [switchingMode, setSwitchingMode] = useState(false);
  const [savingSoundPref, setSavingSoundPref] = useState(false);

  // Monitoring state
  const [monitoringStatus, setMonitoringStatus] =
    useState<MonitoringStatusResponse | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<AlertResponse[]>([]);
  const [recentAiEvents, setRecentAiEvents] = useState<AiEventResponse[]>([]);
  const [ackedAlertIds, setAckedAlertIds] = useState<Set<string>>(new Set());
  const [interventionState, setInterventionState] =
    useState<InterventionStateResponse | null>(null);
  const [calibrationStatus, setCalibrationStatus] = useState<{
    is_calibrating: boolean;
    calibration_progress: number;
    profile_ready: boolean;
  } | null>(null);
  const [ergonomicReminderText, setErgonomicReminderText] = useState<
    string | null
  >(null);
  const [isEyeRestOpen, setIsEyeRestOpen] = useState(false);
  const [eyeRestSecondsRemaining, setEyeRestSecondsRemaining] =
    useState(EYE_REST_OVERLAY_SEC);
  const [eyeRestNextPromptSec, setEyeRestNextPromptSec] =
    useState(EYE_REST_CADENCE_SEC);

  // WebSocket stream metrics (single source of truth for monitoring panel UI)
  const [streamMetrics, setStreamMetrics] =
    useState<CameraStreamMetrics | null>(null);
  const [postureState, setPostureState] = useState<{
    code: string | null;
    message: string | null;
  }>({ code: null, message: null });
  const pythonFps = streamMetrics?.pythonMainFps ?? null;
  const pythonCameraFps = streamMetrics?.pythonCameraFps ?? null;
  const pythonAiFps = streamMetrics?.pythonAiFps ?? null;
  const webFps = streamMetrics?.webFps ?? null;
  const frameLatency = streamMetrics?.frameLatencyMs ?? null;

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const previousCriticalCountRef = useRef(0);
  const ergonomicLastShownAtRef = useRef<number>(0);
  const autoPausedByInterventionRef = useRef(false);

  const [timer, dispatch] = useReducer(timerReducer, {
    status: "idle",
    secondsLeft: 0,
    blockType: "focus",
    cycleCount: 0,
    session: null,
    currentBlock: null,
  });
  const [pendingStart, setPendingStart] = useState<{
    session: StudySession;
    block: SessionBlock;
  } | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resumeAttemptedRef = useRef(false);
  const pendingStartTimeRef = useRef<number | null>(null);
  const recalibrateCalledRef = useRef(false);
  const queryTaskAppliedRef = useRef(false);

  const persistActiveSession = useCallback(
    (sessionId: string, blockId: string) => {
      if (typeof window === "undefined") return;
      localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
      localStorage.setItem(BLOCK_STORAGE_KEY, blockId);
    },
    [],
  );

  const clearPersistedSession = useCallback(() => {
    if (typeof window === "undefined") return;
    localStorage.removeItem(SESSION_STORAGE_KEY);
    localStorage.removeItem(BLOCK_STORAGE_KEY);
  }, []);

  const sameAlertList = (a: AlertResponse[], b: AlertResponse[]) => {
    if (a.length !== b.length) return false;
    if (a.length === 0) return true;
    return (
      String(a[0]?.alert_id) === String(b[0]?.alert_id) &&
      String(a[a.length - 1]?.alert_id) === String(b[b.length - 1]?.alert_id)
    );
  };

  const sameEventList = (a: AiEventResponse[], b: AiEventResponse[]) => {
    if (a.length !== b.length) return false;
    if (a.length === 0) return true;
    return (
      String(a[0]?.event_id) === String(b[0]?.event_id) &&
      String(a[a.length - 1]?.event_id) === String(b[b.length - 1]?.event_id)
    );
  };

  // ── Monitoring polling ────────────────────────────────────────────────────
  const pollMonitoring = useCallback(async (sessionId: string) => {
    try {
      const [status, alerts, events, intervention, calibration] =
        await Promise.all([
          apiFetch<MonitoringStatusResponse>("/api/v1/monitoring/status"),
          apiFetch<AlertResponse[]>(
            `/api/v1/alerts/?session_id=${sessionId}&limit=20`,
          ),
          apiFetch<AiEventResponse[]>(
            `/api/v1/ai-events/?session_id=${sessionId}&limit=20`,
          ),
          apiFetch<InterventionStateResponse>(
            `/api/v1/monitoring/interventions/${sessionId}`,
          ),
          apiFetch<{
            is_calibrating: boolean;
            calibration_progress: number;
            profile_ready: boolean;
          }>("/api/v1/monitoring/calibration-status"),
        ]);
      setMonitoringStatus((prev) => {
        if (
          prev?.status === status.status &&
          prev?.active_mode === status.active_mode &&
          prev?.pid === status.pid
        ) {
          return prev;
        }
        return status;
      });
      setRecentAlerts((prev) => (sameAlertList(prev, alerts) ? prev : alerts));
      setRecentAiEvents((prev) =>
        sameEventList(prev, events) ? prev : events,
      );
      setInterventionState((prev) => {
        if (
          prev?.escalation_level === intervention.escalation_level &&
          prev?.pause_reason === intervention.pause_reason &&
          prev?.resume_countdown_sec === intervention.resume_countdown_sec &&
          prev?.last_update_ts === intervention.last_update_ts
        ) {
          return prev;
        }
        return intervention;
      });
      setCalibrationStatus((prev) => {
        if (
          prev?.is_calibrating === calibration.is_calibrating &&
          prev?.calibration_progress === calibration.calibration_progress &&
          prev?.profile_ready === calibration.profile_ready
        ) {
          return prev;
        }
        return calibration;
      });
    } catch {
      // ignore transient poll errors — show last known state
    }
  }, []);

  useEffect(() => {
    const sessionId =
      timer.session?.session_id ?? pendingStart?.session.session_id;
    if ((timer.status !== "idle" || pendingStart) && sessionId) {
      // immediate first poll then every 3 s
      void pollMonitoring(sessionId);
      pollingRef.current = setInterval(
        () => void pollMonitoring(sessionId),
        3000,
      );
    } else {
      if (pollingRef.current) clearInterval(pollingRef.current);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [timer.status, timer.session?.session_id, pendingStart, pollMonitoring]);

  useEffect(() => {
    if (pendingStart && step === "idle") {
      setStep("calibrating");
    }
  }, [pendingStart, step]);

  const handleCameraMetrics = useCallback((metrics: CameraStreamMetrics) => {
    setStreamMetrics(metrics);
  }, []);

  const handlePostureStateChange = useCallback(
    (posture: { code: string | null; message: string | null }) => {
      setPostureState(posture);
    },
    [],
  );

  const posturePanelTone = useMemo(() => {
    switch (postureState.code) {
      case "ERR_MISSING":
        return {
          box: "border-rose-300 bg-rose-50",
          text: "text-rose-800",
          badge: "bg-rose-100 text-rose-800",
        };
      case "ERR_SLUMP":
        return {
          box: "border-amber-300 bg-amber-50",
          text: "text-amber-800",
          badge: "bg-amber-100 text-amber-800",
        };
      case "ERR_LEANING":
        return {
          box: "border-sky-300 bg-sky-50",
          text: "text-sky-800",
          badge: "bg-sky-100 text-sky-800",
        };
      default:
        return {
          box: "border-slate-200 bg-slate-50",
          text: "text-slate-700",
          badge: "bg-slate-100 text-slate-700",
        };
    }
  }, [postureState.code]);

  // Derived: unacked critical alerts
  const normalizedStatus = normalizeMonitoringStatus(monitoringStatus);
  const criticalEventTypes =
    normalizedStatus.severityDefaults.critical ?? DEFAULT_CRITICAL_EVENT_TYPES;
  const latestAiEvent = recentAiEvents[0] ?? null;
  const latestAiPayload =
    latestAiEvent && typeof latestAiEvent.payload_json === "object"
      ? (latestAiEvent.payload_json as Record<string, unknown>)
      : null;
  const latestFocusScore =
    latestAiPayload && typeof latestAiPayload.focus_score === "number"
      ? latestAiPayload.focus_score
      : null;
  const latestPhoneEvent = recentAiEvents.find((event) =>
    PHONE_EVENT_TYPES.includes(event.event_type),
  );
  const phoneEventAgeMs = latestPhoneEvent
    ? Date.now() - new Date(latestPhoneEvent.start_at).getTime()
    : Number.POSITIVE_INFINITY;
  const isPhoneDetectedLive =
    Number.isFinite(phoneEventAgeMs) && phoneEventAgeMs <= 20000;
  const phoneDetectionCountThisSession = recentAiEvents.filter((event) =>
    PHONE_EVENT_TYPES.includes(event.event_type),
  ).length;
  const aiEventAgeMs = latestAiEvent
    ? Date.now() - new Date(latestAiEvent.start_at).getTime()
    : Number.POSITIVE_INFINITY;
  const isAiProcessingLive =
    (normalizedStatus.status === "active" ||
      normalizedStatus.status === "degraded") &&
    Number.isFinite(aiEventAgeMs) &&
    aiEventAgeMs <= 45000;
  const unackedCriticalAlerts = pickUnackedCriticalAlerts(
    recentAlerts,
    ackedAlertIds,
    criticalEventTypes,
  );

  const selectedMode = normalizeMonitoringMode(
    normalizedStatus.activeMode ?? settings?.monitoring_mode,
  );
  const criticalSoundEnabled = settings?.critical_sound_enabled ?? true;

  // Compute FPS status color (Green/Yellow/Red)
  const getStatusColor = (fps: number | null): string => {
    if (fps === null) return "gray";
    if (fps >= 20) return "green";
    if (fps >= 10) return "yellow";
    return "red";
  };

  const fpsStatusColor = getStatusColor(pythonFps);
  const fpsStatusLabel =
    pythonFps === null
      ? "Offline"
      : pythonFps >= 20
        ? "Optimal"
        : pythonFps >= 10
          ? "Acceptable"
          : "Degraded";

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

  useEffect(() => {
    if (queryTaskAppliedRef.current || !queryTaskId || tasks.length === 0)
      return;
    if (tasks.some((task) => task.task_id === queryTaskId)) {
      setSelectedTaskId(queryTaskId);
      queryTaskAppliedRef.current = true;
    }
  }, [queryTaskId, tasks]);

  useEffect(() => {
    if (resumeAttemptedRef.current || !settings) return;
    resumeAttemptedRef.current = true;
    if (typeof window === "undefined") return;

    const savedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
    const savedBlockId = localStorage.getItem(BLOCK_STORAGE_KEY);
    if (!savedSessionId || !savedBlockId) return;

    const resumeSession = async () => {
      try {
        const session = await apiFetch<StudySession>(
          `/api/v1/sessions/${savedSessionId}`,
        );
        if (session.ended_at) {
          clearPersistedSession();
          return;
        }

        const blocks = await apiFetch<SessionBlock[]>(
          `/api/v1/blocks/session/${session.session_id}`,
        );
        if (blocks.length === 0) {
          clearPersistedSession();
          return;
        }

        const latestBlock = blocks.reduce((latest, item) => {
          if (!latest) return item;
          return new Date(item.started_at).getTime() >
            new Date(latest.started_at).getTime()
            ? item
            : latest;
        }, blocks[0]);

        const latestEndMs = blocks.reduce((maxTs, item) => {
          if (!item.ended_at) return maxTs;
          return Math.max(maxTs, new Date(item.ended_at).getTime());
        }, 0);

        const startedAtMs = new Date(session.started_at).getTime();
        const progressedMs = latestEndMs > 0 ? latestEndMs : Date.now();
        const elapsedSec = Math.max(
          0,
          Math.floor((progressedMs - startedAtMs) / 1000),
        );
        const restoredSeconds = Math.max(
          0,
          latestBlock.planned_duration_seconds - elapsedSec,
        );

        setStep("studying");
        dispatch({
          type: "START",
          session,
          block: latestBlock,
          seconds: restoredSeconds,
        });
        persistActiveSession(session.session_id, latestBlock.block_id);

        if (session.task_id) {
          setSelectedTaskId(session.task_id);
          queryTaskAppliedRef.current = true;
        }
      } catch {
        clearPersistedSession();
      }
    };

    void resumeSession();
  }, [clearPersistedSession, persistActiveSession, settings]);

  useEffect(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }

    const blockId = timer.currentBlock?.block_id;
    if (!timer.session || !blockId || timer.status === "idle") return;

    const sendHeartbeat = async () => {
      try {
        await apiFetch<SessionBlock>(`/api/v1/blocks/${blockId}/heartbeat`, {
          method: "PATCH",
          body: JSON.stringify({ ended_at: new Date().toISOString() }),
        });
      } catch {
        // Keep learning flow uninterrupted on transient network/backend errors.
      }
    };

    void sendHeartbeat();
    heartbeatRef.current = setInterval(() => {
      void sendHeartbeat();
    }, HEARTBEAT_INTERVAL_MS);

    return () => {
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
    };
  }, [timer.currentBlock?.block_id, timer.session, timer.status]);

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

  // Get selected task's estimated time if available, otherwise use global settings
  const selectedTask = tasks.find((t) => t.task_id === selectedTaskId);
  const focusSec = selectedTask?.estimated_minutes
    ? selectedTask.estimated_minutes * 60
    : (settings?.pomodoro_focus_minutes ?? 25) * 60;
  const breakSec = (settings?.pomodoro_break_minutes ?? 5) * 60;
  const longBreakSec = (settings?.pomodoro_long_break_minutes ?? 15) * 60;
  const cyclesBeforeLong = settings?.pomodoro_cycles_before_long_break ?? 4;

  useEffect(() => {
    if (!pendingStart || !calibrationStatus) return;

    if (calibrationStatus.is_calibrating) {
      setStartupCalibrationMessage(
        `Đang lấy profile cá nhân: ${Math.round(calibrationStatus.calibration_progress)}%`,
      );
      return;
    }

    setStartupCalibrationMessage(
      calibrationStatus.profile_ready
        ? "Profile cá nhân đã sẵn sàng. Bắt đầu phiên học!"
        : "Bắt đầu phiên học (không có profile cá nhân).",
    );

    dispatch({
      type: "START",
      session: pendingStart.session,
      block: pendingStart.block,
      seconds: focusSec,
    });
    setPendingStart(null);

    setTimeout(() => setStartupCalibrationMessage(null), 2000);
  }, [pendingStart, calibrationStatus, focusSec]);

  useEffect(() => {
    if (pendingStart) {
      pendingStartTimeRef.current = Date.now();
    } else {
      pendingStartTimeRef.current = null;
    }
  }, [pendingStart]);

  useEffect(() => {
    if (!pendingStart) return;

    const timeout = setTimeout(() => {
      if (!pendingStart) return;
      console.warn("Calibration timeout fallback: forcing session start");
      setStartupCalibrationMessage("Bắt đầu phiên học (calibration timeout).");
      dispatch({
        type: "START",
        session: pendingStart.session,
        block: pendingStart.block,
        seconds: focusSec,
      });
      setPendingStart(null);
      setTimeout(() => setStartupCalibrationMessage(null), 2000);
    }, 15000);

    return () => clearTimeout(timeout);
  }, [pendingStart, focusSec]);

  const handleStart = async () => {
    if (!settings) return;
    setStarting(true);
    setError(null);
    setStartupCalibrationMessage(null);
    setPendingStart(null);
    setStep("calibrating");
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
      persistActiveSession(session.session_id, block.block_id);

      // Bật giám sát AI nếu được bật trong settings
      if (settings.ai_monitoring_enabled !== false) {
        try {
          const preferredMode = normalizeMonitoringMode(
            settings.monitoring_mode,
          );
          const status = await apiFetch<MonitoringStatusResponse>(
            "/api/v1/monitoring/start",
            {
              method: "POST",
              body: JSON.stringify({
                session_id: session.session_id,
                show_display: shouldShowExternalDisplay(preferredMode),
              }),
            },
          );
          setMonitoringStatus(status);

          setStartupCalibrationMessage(
            "Đang lấy profile cá nhân trong 10 giây trước khi bắt đầu phiên học...",
          );
          setPendingStart({ session, block });

          // Trigger fresh personal-profile calibration in background.
          // Do not block UI/session bootstrap on calibration request latency.
          if (!recalibrateCalledRef.current) {
            recalibrateCalledRef.current = true;
            void apiFetch<{
              accepted: boolean;
              message: string;
              start_error?: string | null;
            }>("/api/v1/monitoring/recalibrate-profile", {
              method: "POST",
            }).catch(() => {
              // Ignore recalibration request failures; session can continue.
            });
          }
        } catch (monitoringError: unknown) {
          setMonitoringStatus(null);
          setStep("idle");
          setError(
            monitoringError instanceof Error
              ? `Monitoring failed to start: ${monitoringError.message}`
              : "Monitoring failed to start",
          );
          return;
        }
      } else {
        setStep("studying");
        dispatch({ type: "START", session, block, seconds: focusSec });
      }
    } catch (e: unknown) {
      clearPersistedSession();
      setStep("idle");
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
      await apiFetch(
        `/api/v1/blocks/session/${timer.session.session_id}/close-latest`,
        {
          method: "POST",
        },
      );
      const block = await apiFetch<SessionBlock>("/api/v1/blocks/", {
        method: "POST",
        body: JSON.stringify({
          session_id: timer.session.session_id,
          block_type: nextType,
          start_at: new Date().toISOString(),
          planned_duration_seconds: nextSec,
        } satisfies BlockCreate),
      });
      persistActiveSession(timer.session.session_id, block.block_id);
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
      await apiFetch(
        `/api/v1/blocks/session/${timer.session.session_id}/close-latest`,
        {
          method: "POST",
        },
      );
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
    clearPersistedSession();
    setStreamMetrics(null);
    setPostureState({ code: null, message: null });
    setMonitoringStatus(null);
    setRecentAlerts([]);
    setPendingStart(null);
    recalibrateCalledRef.current = false;
    setStep("idle");
    dispatch({ type: "STOP" });
  };

  const handleRetryMonitoring = async () => {
    if (!timer.session) return;
    try {
      const modeForRetry = normalizeMonitoringMode(
        settings?.monitoring_mode ?? monitoringStatus?.active_mode,
      );
      const status = await apiFetch<MonitoringStatusResponse>(
        "/api/v1/monitoring/start",
        {
          method: "POST",
          body: JSON.stringify({
            session_id: timer.session.session_id,
            show_display: shouldShowExternalDisplay(modeForRetry),
          }),
        },
      );
      if (modeForRetry !== "alerts_only") {
        const switched = await apiFetch<ModeSwitchResponse>(
          "/api/v1/monitoring/mode",
          {
            method: "POST",
            body: JSON.stringify({ mode: modeForRetry }),
          },
        );
        setMonitoringStatus({
          ...status,
          status: switched.status,
          active_mode: switched.applied_mode,
          degraded_reason: switched.degraded_reason,
        });
      } else {
        setMonitoringStatus(status);
      }
    } catch {
      // keep degraded banner visible
    }
  };

  const handleSwitchMode = async (mode: string) => {
    setSwitchingMode(true);
    setError(null);
    try {
      const isMonitoringRunning =
        normalizedStatus.status === "active" ||
        normalizedStatus.status === "degraded";

      if (mode !== "alerts_only" && !timer.session) {
        setError(
          "Start a study session before switching to camera monitoring modes.",
        );
        return;
      }

      if (mode !== "alerts_only" && timer.session && !isMonitoringRunning) {
        const started = await apiFetch<MonitoringStatusResponse>(
          "/api/v1/monitoring/start",
          {
            method: "POST",
            body: JSON.stringify({
              session_id: timer.session.session_id,
              show_display: shouldShowExternalDisplay(mode),
            }),
          },
        );
        setMonitoringStatus(started);
      }

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

      // Reconfigure subprocess display behavior immediately for camera modes.
      if (
        timer.session &&
        (res.applied_mode === "browser_camera" ||
          res.applied_mode === "external_camera") &&
        (normalizedStatus.status === "active" ||
          normalizedStatus.status === "degraded")
      ) {
        const restarted = await apiFetch<MonitoringStatusResponse>(
          "/api/v1/monitoring/start",
          {
            method: "POST",
            body: JSON.stringify({
              session_id: timer.session.session_id,
              show_display: shouldShowExternalDisplay(res.applied_mode),
            }),
          },
        );
        setMonitoringStatus(restarted);
      }
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

  const handleRecalibrateProfile = async () => {
    setError(null);
    try {
      const res = await apiFetch<{
        accepted: boolean;
        message: string;
        start_error?: string | null;
      }>("/api/v1/monitoring/recalibrate-profile", { method: "POST" });
      if (!res.accepted) {
        setError(
          res.start_error
            ? `Calibration restart failed: ${res.start_error}`
            : `Calibration restart failed: ${res.message}`,
        );
      }
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to start recalibration",
      );
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

  // Sync timer run/pause with backend intervention state.
  useEffect(() => {
    if (!interventionState) return;

    if (
      interventionState.escalation_level === "paused" &&
      timer.status === "running"
    ) {
      autoPausedByInterventionRef.current = true;
      dispatch({ type: "PAUSE" });
      return;
    }

    if (
      interventionState.escalation_level === "none" &&
      autoPausedByInterventionRef.current &&
      timer.status === "paused"
    ) {
      autoPausedByInterventionRef.current = false;
      dispatch({ type: "RESUME" });
    }
  }, [interventionState, timer.status]);

  // Gentle ergonomic reminder with anti-spam throttling.
  useEffect(() => {
    const ergonomicEvent = recentAiEvents.find((event) =>
      ERGONOMIC_EVENT_TYPES.includes(event.event_type),
    );

    if (!ergonomicEvent) {
      setErgonomicReminderText(null);
      return;
    }

    const eventAgeMs = Date.now() - new Date(ergonomicEvent.start_at).getTime();
    if (eventAgeMs > ERGONOMIC_ACTIVE_WINDOW_MS) {
      setErgonomicReminderText(null);
      return;
    }

    const now = Date.now();
    if (
      now - ergonomicLastShownAtRef.current < ERGONOMIC_REMINDER_COOLDOWN_MS &&
      ergonomicReminderText
    ) {
      return;
    }

    ergonomicLastShownAtRef.current = now;

    if (
      ergonomicEvent.event_type.includes("close") ||
      ergonomicEvent.event_type.includes("near")
    ) {
      setErgonomicReminderText(
        "You are sitting too close to the screen. Lean back to protect your eyes.",
      );
      return;
    }

    setErgonomicReminderText(
      "Posture check: lift your chest, relax shoulders, and align your neck.",
    );
  }, [recentAiEvents, ergonomicReminderText]);

  // 20-20-20 cadence countdown while running focus blocks.
  useEffect(() => {
    if (
      timer.status !== "running" ||
      timer.blockType !== "focus" ||
      isEyeRestOpen
    ) {
      return;
    }

    const cadenceTick = setInterval(() => {
      setEyeRestNextPromptSec((prev) => {
        if (prev <= 1) {
          setIsEyeRestOpen(true);
          setEyeRestSecondsRemaining(EYE_REST_OVERLAY_SEC);
          return EYE_REST_CADENCE_SEC;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(cadenceTick);
  }, [timer.status, timer.blockType, isEyeRestOpen]);

  // Overlay countdown for optional 20-second eye-rest.
  useEffect(() => {
    if (!isEyeRestOpen) return;

    const overlayTick = setInterval(() => {
      setEyeRestSecondsRemaining((prev) => {
        if (prev <= 1) {
          setIsEyeRestOpen(false);
          return EYE_REST_OVERLAY_SEC;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(overlayTick);
  }, [isEyeRestOpen]);

  const dismissEyeRestOverlay = () => {
    setIsEyeRestOpen(false);
    setEyeRestSecondsRemaining(EYE_REST_OVERLAY_SEC);
  };

  const completeEyeRestOverlay = () => {
    setIsEyeRestOpen(false);
    setEyeRestSecondsRemaining(EYE_REST_OVERLAY_SEC);
  };

  const eyeRestCadenceLabel = formatTime(eyeRestNextPromptSec);
  const activeSessionId =
    timer.session?.session_id ?? pendingStart?.session.session_id ?? null;

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

  const showStudying = step === "studying" || timer.status !== "idle";

  if (pendingStart) {
    return (
      <div className="app-page mx-auto max-w-5xl space-y-4">
        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}
        <div className="surface-card max-w-xl space-y-4 p-6">
          <h2 className="font-semibold text-slate-800">
            Đang lấy profile cá nhân...
          </h2>
          <p className="text-sm text-slate-600">
            Vui lòng ngồi thẳng và nhìn vào camera trong 10 giây.
          </p>
          {startupCalibrationMessage && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {startupCalibrationMessage}
            </div>
          )}
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-amber-500 transition-all duration-300"
              style={{
                width: `${Math.max(0, Math.min(100, calibrationStatus?.calibration_progress ?? 0))}%`,
              }}
            />
          </div>
          <p className="text-right text-xs text-slate-500">
            {Math.round(calibrationStatus?.calibration_progress ?? 0)}%
          </p>
          <CameraWidget
            sessionId={pendingStart.session.session_id}
            className="w-full min-h-[160px]"
            onMetrics={handleCameraMetrics}
            onCalibrationComplete={() => setStep("studying")}
          />
          <button
            onClick={() => {
              dispatch({
                type: "START",
                session: pendingStart.session,
                block: pendingStart.block,
                seconds: focusSec,
              });
              setPendingStart(null);
              setStep("studying");
              setStartupCalibrationMessage(null);
            }}
            className="btn-soft w-full text-sm"
          >
            Bỏ qua, bắt đầu ngay
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-page mx-auto max-w-5xl">
      <div>
        <h1 className="page-title">Study Timer</h1>
        <p className="page-subtitle">
          Keep momentum with adaptive monitoring, clear alerts, and smooth
          session control.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {startupCalibrationMessage && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {startupCalibrationMessage}
        </div>
      )}

      {step === "idle" ? (
        <div className="surface-card max-w-xl space-y-4 p-6">
          <div>
            <label className="field-label">Task (optional)</label>
            <select
              value={selectedTaskId}
              onChange={(e) => setSelectedTaskId(e.target.value)}
              className="field-select"
            >
              <option value="">No task selected</option>
              {tasks.map((t) => (
                <option key={t.task_id} value={t.task_id}>
                  {t.title}
                </option>
              ))}
            </select>
          </div>

          {settings && (
            <div className="rounded-xl border border-slate-200 bg-white/70 p-3 text-xs text-slate-600 space-y-1">
              <p>Focus: {settings.pomodoro_focus_minutes} min</p>
              <p>Short break: {settings.pomodoro_break_minutes} min</p>
              <p>Long break: {settings.pomodoro_long_break_minutes} min</p>
              <p>
                Cycles before long break:{" "}
                {settings.pomodoro_cycles_before_long_break}
              </p>
              {settings.ai_monitoring_enabled !== false && (
                <p className="text-cyan-700">
                  AI monitoring:{" "}
                  {MODE_LABELS[settings.monitoring_mode ?? "browser_camera"] ??
                    "Browser camera"}
                </p>
              )}
              {settings.ai_monitoring_enabled !== false &&
                (settings.monitoring_mode ?? "browser_camera") !==
                  "alerts_only" && (
                  <p className="text-cyan-700">
                    Web camera feed sẽ xuất hiện sau khi bạn bấm Start Pomodoro.
                  </p>
                )}
            </div>
          )}

          <button
            onClick={handleStart}
            disabled={starting || !settings || pendingStart !== null}
            className="btn-primary w-full disabled:opacity-60"
          >
            {starting ? "Starting..." : "Start Pomodoro"}
          </button>
        </div>
      ) : showStudying ? (
        <div className="space-y-4">
          {interventionState?.escalation_level === "warning" && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Attention drifting. Stay on task to avoid auto-pause.
            </div>
          )}

          {interventionState?.escalation_level === "paused" && (
            <div className="rounded-xl border border-indigo-300 bg-indigo-50 px-4 py-3 text-sm text-indigo-800">
              Session paused by intervention:{" "}
              {interventionState.pause_reason ?? "unknown"}.
              {interventionState.resume_countdown_sec !== null &&
                ` Resume in ${Math.ceil(interventionState.resume_countdown_sec)}s.`}
            </div>
          )}

          {ergonomicReminderText && (
            <div className="rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-cyan-800">
              {ergonomicReminderText}
            </div>
          )}

          {settings?.ai_monitoring_enabled !== false && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 space-y-2">
              <div className="flex items-center justify-between gap-3">
                <span className="font-semibold">Profile calibration</span>
                <button
                  onClick={handleRecalibrateProfile}
                  className="rounded-md border border-amber-300 bg-white px-3 py-1 text-xs font-semibold text-amber-800 hover:bg-amber-100"
                >
                  Re-calibrate profile
                </button>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-amber-100">
                <div
                  className="h-full rounded-full bg-amber-500 transition-all duration-300"
                  style={{
                    width: `${Math.max(0, Math.min(100, calibrationStatus?.calibration_progress ?? 0))}%`,
                  }}
                />
              </div>
              <div className="flex items-center justify-between text-xs">
                <span>
                  {calibrationStatus?.is_calibrating
                    ? `Calibrating ${Math.round(calibrationStatus.calibration_progress)}%`
                    : calibrationStatus?.profile_ready
                      ? "Profile cá nhân đã sẵn sàng"
                      : "Chưa có profile cá nhân"}
                </span>
                <span className="text-amber-700">
                  {Math.round(calibrationStatus?.calibration_progress ?? 0)}%
                </span>
              </div>
            </div>
          )}

          {isPhoneDetectedLive && (
            <div className="rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              Phone usage detected. Put your phone down to protect focus mode.
            </div>
          )}

          {/* ── Critical alert bar ── */}
          {unackedCriticalAlerts.length > 0 && (
            <div className="rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-rose-700">
                  Critical Alert
                  {unackedCriticalAlerts.length > 1 &&
                    ` (${unackedCriticalAlerts.length})`}
                </span>
                <button
                  onClick={handleAckAll}
                  className="text-xs font-semibold text-rose-700 underline hover:text-rose-800"
                >
                  Dismiss all
                </button>
              </div>
              <p className="text-sm text-rose-700">
                {unackedCriticalAlerts[0].message ??
                  "High-severity event detected"}
              </p>
              {unackedCriticalAlerts.length === 1 && (
                <button
                  onClick={() =>
                    handleAckAlert(String(unackedCriticalAlerts[0].alert_id))
                  }
                  className="text-xs font-semibold text-rose-700 underline hover:text-rose-800"
                >
                  Dismiss
                </button>
              )}
            </div>
          )}

          {settings?.ai_monitoring_enabled !== false && (
            <div
              className={`rounded-xl border px-4 py-3 space-y-2 ${posturePanelTone.box}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className={`text-sm font-semibold ${posturePanelTone.text}`}
                >
                  Posture status
                </span>
                <span
                  className={`rounded px-2 py-1 text-[11px] font-semibold ${posturePanelTone.badge}`}
                >
                  {postureState.code ?? "OK"}
                </span>
              </div>
              <p className={`text-sm ${posturePanelTone.text}`}>
                {postureState.message ?? "Tư thế ổn định."}
              </p>
            </div>
          )}

          {/* ── Main timer card ── */}
          <div className="surface-card surface-card-strong p-6 text-center space-y-4">
            <p
              className={`text-lg font-semibold ${BLOCK_COLOR[timer.blockType]}`}
            >
              {BLOCK_LABEL[timer.blockType]}
            </p>

            <p className="text-6xl font-mono font-bold text-slate-900">
              {formatTime(timer.secondsLeft)}
            </p>

            {/* Progress bar */}
            <div className="h-2 w-full rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-cyan-500 to-sky-600 transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>

            <p className="text-sm text-slate-600">
              Cycle {timer.cycleCount === 0 ? 1 : timer.cycleCount} -{" "}
              {timer.cycleCount} focus block{timer.cycleCount !== 1 ? "s" : ""}{" "}
              completed
            </p>

            {timer.blockType === "focus" && (
              <p className="rounded-lg border border-teal-200 bg-teal-50 px-2 py-1 text-xs text-teal-700">
                20-20-20 reminder in {eyeRestCadenceLabel}
              </p>
            )}

            <div className="flex justify-center gap-3">
              {timer.status === "running" ? (
                <button
                  onClick={() => dispatch({ type: "PAUSE" })}
                  className="btn-soft"
                >
                  Pause
                </button>
              ) : (
                <button
                  onClick={() => dispatch({ type: "RESUME" })}
                  className="btn-primary"
                >
                  Resume
                </button>
              )}
              <button onClick={handleStop} className="btn-danger">
                Stop
              </button>
            </div>
          </div>

          {/* ── Monitoring widget ── */}
          {settings?.ai_monitoring_enabled !== false && (
            <div className="surface-card p-4 text-sm space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-800">
                  AI Monitoring
                </span>
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
                <p className="text-xs text-slate-500">
                  Mode:{" "}
                  {MODE_LABELS[normalizedStatus.activeMode] ??
                    normalizedStatus.activeMode}
                </p>
              )}
              <div
                className={`rounded border px-2 py-1.5 text-xs ${
                  isAiProcessingLive
                    ? "border-green-200 bg-green-50 text-green-700"
                    : "border-amber-200 bg-amber-50 text-amber-700"
                }`}
              >
                <p className="font-medium">
                  AI processing:{" "}
                  {isAiProcessingLive ? "Live" : "No recent AI signal"}
                </p>
                {latestAiEvent && (
                  <p className="mt-1">
                    Last event: {latestAiEvent.event_type}
                    {latestFocusScore !== null
                      ? ` - Focus ${latestFocusScore}%`
                      : ""}
                  </p>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Phone detected in recent window:{" "}
                {phoneDetectionCountThisSession}
              </p>
              <div className="grid grid-cols-1 gap-2 pt-1">
                <label className="field-label mb-0">Monitoring mode</label>
                <select
                  value={selectedMode}
                  onChange={(e) => void handleSwitchMode(e.target.value)}
                  disabled={switchingMode}
                  className="field-select text-xs disabled:opacity-60"
                >
                  {MONITORING_MODES.map((mode) => (
                    <option key={mode} value={mode}>
                      {MODE_LABELS[mode]}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center justify-between rounded-lg border border-slate-200 bg-white/70 px-2 py-1.5">
                <span className="text-xs text-slate-600">
                  Critical alert sound
                </span>
                <input
                  type="checkbox"
                  checked={criticalSoundEnabled}
                  disabled={savingSoundPref}
                  onChange={(e) =>
                    void handleToggleCriticalSound(e.target.checked)
                  }
                  className="h-4 w-4 rounded border-slate-300 text-cyan-600"
                />
              </label>
              {selectedMode !== "alerts_only" &&
                (normalizedStatus.status === "active" ||
                normalizedStatus.status === "degraded" ? (
                  <CameraWidget
                    sessionId={activeSessionId}
                    className="w-full min-h-[140px] border border-slate-200/80"
                    onMetrics={handleCameraMetrics}
                    onPostureStateChange={handlePostureStateChange}
                  />
                ) : (
                  <div className="rounded-xl border border-slate-200 bg-white/70 px-3 py-3 text-xs text-slate-600">
                    Web camera đang chờ phiên học. Nhấn{" "}
                    <strong>Start Pomodoro</strong> để bật stream camera trên
                    web.
                  </div>
                ))}
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

          {/* ── Telemetry FPS widget ── */}
          {monitoringStatus?.status === "active" &&
            selectedMode !== "alerts_only" && (
              <div
                className={`rounded-xl border p-3 space-y-2 ${
                  fpsStatusColor === "green"
                    ? "border-emerald-200 bg-emerald-50"
                    : fpsStatusColor === "yellow"
                      ? "border-amber-200 bg-amber-50"
                      : "border-rose-200 bg-rose-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-700">
                    Performance Metrics
                  </span>
                  <span
                    className={`rounded px-2 py-1 text-xs font-medium ${
                      fpsStatusColor === "green"
                        ? "bg-emerald-100 text-emerald-800"
                        : fpsStatusColor === "yellow"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {fpsStatusLabel}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded border border-slate-200 bg-white/85 px-2 py-1.5">
                    <p className="text-slate-600">Python Main FPS</p>
                    <p className="font-mono font-bold text-slate-900">
                      {pythonFps !== null ? pythonFps : "—"}
                    </p>
                  </div>
                  <div className="rounded border border-slate-200 bg-white/85 px-2 py-1.5">
                    <p className="text-slate-600">Web FPS</p>
                    <p className="font-mono font-bold text-slate-900">
                      {webFps !== null ? webFps.toFixed(1) : "—"}
                    </p>
                  </div>
                  <div className="rounded border border-slate-200 bg-white/85 px-2 py-1.5">
                    <p className="text-slate-600">Python Camera FPS</p>
                    <p className="font-mono font-bold text-slate-900">
                      {pythonCameraFps !== null ? pythonCameraFps : "—"}
                    </p>
                  </div>
                  <div className="rounded border border-slate-200 bg-white/85 px-2 py-1.5">
                    <p className="text-slate-600">Python AI FPS</p>
                    <p className="font-mono font-bold text-slate-900">
                      {pythonAiFps !== null ? pythonAiFps : "—"}
                    </p>
                  </div>
                  {frameLatency !== null && (
                    <div className="col-span-2 rounded border border-slate-200 bg-white/85 px-2 py-1.5">
                      <p className="text-slate-600">Latency</p>
                      <p className="font-mono font-bold text-slate-900">
                        {frameLatency}ms
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

          <WhiteNoiseControl />
        </div>
      ) : (
        <div className="surface-card max-w-xl p-6 text-sm text-slate-600">
          Preparing study session...
        </div>
      )}

      <BreakOverlay202020
        isOpen={isEyeRestOpen}
        secondsRemaining={eyeRestSecondsRemaining}
        onDismiss={dismissEyeRestOverlay}
        onComplete={completeEyeRestOverlay}
      />
    </div>
  );
}
