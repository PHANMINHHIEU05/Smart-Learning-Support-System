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

  // ========================================================================
  // Render
  // ========================================================================

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      {/* ════════════════════════════════════════════════════════════════ */}
      {/* Title & Status */}
      {/* ════════════════════════════════════════════════════════════════ */}

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
              isDistracted
                ? "text-red-700"
                : alertStatus === "monitoring"
                  ? "text-green-700"
                  : "text-slate-600"
            }`}
          >
            {isDistracted
              ? "⚠️ AI phát hiện xao nhãng - Tạm dừng"
              : alertStatus === "monitoring"
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

      {isDistracted && (
        <div className="mb-8 p-4 bg-red-50 border-2 border-red-200 rounded-lg max-w-md">
          <p className="text-red-800 text-center font-semibold">
            🔴 Phát hiện xao nhãng
          </p>
          <p className="text-red-700 text-sm text-center mt-1">
            Hệ thống AI đã phát hiện bạn đang xao nhãng.
            <br />
            Đồng hồ đã được tạm dừng.
          </p>
        </div>
      )}

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
