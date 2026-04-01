/**
 * PomodoroTimer Component
 *
 * Component Pomodoro đầy đủ với tích hợp AI distraction monitoring.
 *
 * Tính năng:
 * - Đồng hồ Pomodoro cơ bản (25 phút làm việc, 5 phút nghỉ)
 * - Tự động dừng/tiếp tục dựa trên tín hiệu xao nhãng từ backend
 * - Hiển thị chỉ báo xao nhãng nhẹ nhàng (chấm nhấp nháy + text)
 * - Không dùng pop-up/alert (chỉ update state)
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { useAlertListener } from "@/hooks/useAlertListener";
import { apiFetch } from "@/lib/api-client";

interface PomodoroTimerProps {
  sessionId: string;
  workMinutes?: number;
  breakMinutes?: number;
}

export function PomodoroTimer({
  sessionId,
  workMinutes = 25,
  breakMinutes = 5,
}: PomodoroTimerProps) {
  // ========================================================================
  // Timer State
  // ========================================================================

  /** Thời gian còn lại (tính bằng giây) */
  const [timeLeft, setTimeLeft] = useState(workMinutes * 60);

  /** Đồng hồ đang chạy? */
  const [isRunning, setIsRunning] = useState(false);

  /** Đang trong phase làm việc hay nghỉ? */
  const [phase, setPhase] = useState<"work" | "break">("work");
  const [showStartupGuide, setShowStartupGuide] = useState(true);
  const [isRecalibrating, setIsRecalibrating] = useState(false);
  const [calibrationMessage, setCalibrationMessage] = useState<string | null>(
    null,
  );
  const [isCalibratingNow, setIsCalibratingNow] = useState(false);
  const [calibrationProgress, setCalibrationProgress] = useState(0);

  // ========================================================================
  // Callbacks: Pause/Resume Timer
  // ========================================================================

  const pauseTimer = useCallback(() => {
    setIsRunning(false);
  }, []);

  const resumeTimer = useCallback(() => {
    setIsRunning(true);
  }, []);

  // ========================================================================
  // Hook: Lắng nghe cảnh báo xao nhãng
  // ========================================================================

  const { isDistracted, alertStatus, lastAlertAt } = useAlertListener({
    sessionId,
    pauseTimer,
    resumeTimer,
    useWebsocket: true,
    debug: true, // Chuyển sang false trong production
  });

  // ========================================================================
  // Effect: Chạy đồng hồ mỗi giây
  // ========================================================================

  useEffect(() => {
    const timer = setTimeout(() => setShowStartupGuide(false), 12000);
    return () => clearTimeout(timer);
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;

    let active = true;
    const poll = async () => {
      try {
        const state = await apiFetch<{
          ready: boolean;
          is_calibrating: boolean;
          calibration_progress: number;
          profile_ready: boolean;
          start_error?: string | null;
        }>("/api/v1/monitoring/calibration-status");

        if (!active) return;
        setIsCalibratingNow(Boolean(state.is_calibrating));
        setCalibrationProgress(Math.round(state.calibration_progress || 0));

        if (state.is_calibrating) {
          setCalibrationMessage(
            `Dang lay mau tu the: ${Math.round(state.calibration_progress || 0)}%`,
          );
        } else if (state.profile_ready) {
          setCalibrationMessage("Profile ca nhan san sang.");
        }
      } catch {
        if (!active) return;
      }
    };

    void poll();
    const id = setInterval(() => {
      void poll();
    }, 1000);

    return () => {
      active = false;
      clearInterval(id);
    };
  }, [sessionId]);

  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          // ⏰ Hết thời gian phase hiện tại
          setIsRunning(false);

          // Chuyển sang phase tiếp theo
          if (phase === "work") {
            setPhase("break");
            setTimeLeft(breakMinutes * 60);
          } else {
            setPhase("work");
            setTimeLeft(workMinutes * 60);
          }

          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isRunning, phase, workMinutes, breakMinutes]);

  // ========================================================================
  // Helpers: Format Time
  // ========================================================================

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  const handleRecalibrate = useCallback(async () => {
    setIsRecalibrating(true);
    setCalibrationMessage(null);
    try {
      const res = await apiFetch<{
        accepted: boolean;
        message: string;
        start_error?: string | null;
      }>("/api/v1/monitoring/recalibrate-profile", {
        method: "POST",
      });

      if (res.accepted) {
        setCalibrationMessage(
          "Dang lay mau tu the 6 giay. Hay ngoi thang, mat nhin man hinh.",
        );
      } else {
        setCalibrationMessage(
          res.start_error
            ? `Khong the recalibrate: ${res.start_error}`
            : `Khong the recalibrate: ${res.message}`,
        );
      }
    } catch (error) {
      const msg =
        error instanceof Error ? error.message : "Loi goi API recalibrate";
      setCalibrationMessage(`Khong the recalibrate: ${msg}`);
    } finally {
      setIsRecalibrating(false);
    }
  }, []);

  // ========================================================================
  // Render
  // ========================================================================

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      {/* ════════════════════════════════════════════════════════════════ */}
      {/* Title & Status */}
      {/* ════════════════════════════════════════════════════════════════ */}

      {showStartupGuide && (
        <div className="mb-4 max-w-2xl rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-800">
          <p className="text-sm font-semibold">Huong dan bat dau phien hoc</p>
          <p className="text-sm">
            Ban hay ngoi dung tu the trong vai giay dau de he thong lay du lieu
            mau ca nhan.
          </p>
        </div>
      )}

      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-slate-800 mb-2">
          {phase === "work" ? "🎯 Pomodoro" : "☕ Break"}
        </h1>
        <p className="text-slate-600">
          {phase === "work"
            ? "Tập trung và hoàn thành công việc"
            : "Nghỉ ngơi và tái tạo năng lượng"}
        </p>
      </div>

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* AI Distraction Indicator */}
      {/* ════════════════════════════════════════════════════════════════ */}

      <div className="mb-8">
        {/* Chấm tròn nhấp nháy + Text chỉ báo */}
        <div
          className={`flex items-center gap-3 px-4 py-2 rounded-full transition-all duration-300 ${
            isDistracted
              ? "bg-red-50 border-2 border-red-300"
              : alertStatus === "monitoring"
                ? "bg-green-50 border-2 border-green-300"
                : "bg-slate-100 border-2 border-slate-300"
          }`}
        >
          {/* Chấm tròn nhấp nháy */}
          <div
            className={`w-3 h-3 rounded-full ${
              isDistracted
                ? "bg-red-500 animate-pulse" // ❌ Xao nhãng → đỏ nhấp nháy
                : alertStatus === "monitoring"
                  ? "bg-green-500 animate-pulse" // ✅ Giám sát → xanh nhấp nháy
                  : "bg-slate-400" // 🔘 Không kết nối
            }`}
          />

          {/* Text trạng thái */}
          <span
            className={`text-sm font-medium ${
              alertStatus === "monitoring" ? "text-green-700" : "text-slate-600"
            }`}
          >
            {alertStatus === "monitoring"
              ? "✅ AI đang giám sát"
              : "🔘 Kết nối lại..."}
          </span>
        </div>

        {/* Debug: Thời gian lần cuối cảnh báo */}
        {lastAlertAt && (
          <p className="text-xs text-slate-500 mt-2 text-center">
            Lần cuối: {new Date(lastAlertAt).toLocaleTimeString()}
          </p>
        )}

        {calibrationMessage && (
          <p className="text-xs text-slate-600 mt-2 text-center">
            {calibrationMessage}
          </p>
        )}

        {isCalibratingNow ? (
          <div className="mt-2 w-full max-w-xs mx-auto">
            <div className="h-2 w-full rounded bg-amber-100 overflow-hidden">
              <div
                className="h-full bg-amber-500 transition-all duration-300"
                style={{
                  width: `${Math.max(0, Math.min(100, calibrationProgress))}%`,
                }}
              />
            </div>
            <p className="text-xs text-amber-700 mt-1 text-center">
              Calibrating... {calibrationProgress}%
            </p>
          </div>
        ) : null}
      </div>

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* Timer Display */}
      {/* ════════════════════════════════════════════════════════════════ */}

      <div className="mb-8">
        <div className="text-8xl font-bold text-slate-800 font-mono tracking-tighter">
          {formatTime(timeLeft)}
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* Distraction Overlay (khi đang bị xao nhãng) */}
      {/* ════════════════════════════════════════════════════════════════ */}

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* Control Buttons */}
      {/* ════════════════════════════════════════════════════════════════ */}

      <div className="flex gap-4">
        {/* Start/Pause Button */}
        <button
          onClick={() => setIsRunning(!isRunning)}
          disabled={isDistracted} // Không cho start nếu đang bị xao nhãng
          className={`px-8 py-3 rounded-lg font-semibold transition-all ${
            isRunning
              ? "bg-red-500 hover:bg-red-600 text-white"
              : "bg-green-500 hover:bg-green-600 text-white"
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isRunning ? "⏸ Tạm dừng" : "▶ Bắt đầu"}
        </button>

        {/* Reset Button */}
        <button
          onClick={() => {
            setTimeLeft(
              phase === "work" ? workMinutes * 60 : breakMinutes * 60,
            );
            setIsRunning(false);
          }}
          className="px-8 py-3 rounded-lg font-semibold bg-slate-500 hover:bg-slate-600 text-white transition-all"
        >
          🔄 Reset
        </button>

        {/* Skip to Next Phase Button */}
        <button
          onClick={() => {
            if (phase === "work") {
              setPhase("break");
              setTimeLeft(breakMinutes * 60);
            } else {
              setPhase("work");
              setTimeLeft(workMinutes * 60);
            }
            setIsRunning(false);
          }}
          className="px-8 py-3 rounded-lg font-semibold bg-blue-500 hover:bg-blue-600 text-white transition-all"
        >
          ⏭ Bỏ qua
        </button>

        <button
          onClick={handleRecalibrate}
          disabled={isRecalibrating}
          className="px-8 py-3 rounded-lg font-semibold bg-amber-500 hover:bg-amber-600 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRecalibrating ? "...Dang recalibrate" : "Re-calibrate profile"}
        </button>
      </div>

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* Debug Info */}
      {/* ════════════════════════════════════════════════════════════════ */}

      <div className="mt-12 p-4 bg-slate-200 rounded-lg text-xs text-slate-700 max-w-md">
        <p>
          <strong>Debug:</strong>
        </p>
        <p>Session ID: {sessionId}</p>
        <p>Timer Status: {isRunning ? "Running" : "Paused"}</p>
        <p>Distracted: {isDistracted ? "Yes" : "No"}</p>
        <p>Alert Status: {alertStatus}</p>
        <p>Phase: {phase}</p>
      </div>
    </div>
  );
}
