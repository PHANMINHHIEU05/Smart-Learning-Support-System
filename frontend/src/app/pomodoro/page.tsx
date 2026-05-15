/**
 * Pomodoro Page Example
 *
 * Trang demo sử dụng PomodoroTimer component với AI distraction monitoring
 */

"use client";

import { PomodoroTimer } from "@/components/PomodoroTimer";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";

export default function PomodoroPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);

  // ========================================================================
  // Effect: Lấy hoặc tạo sessionId
  // ========================================================================

  useEffect(() => {
    const getOrCreateSessionId = async () => {
      // Kiểm tra localStorage trước
      const stored = localStorage.getItem("pomodoroSessionId");
      if (stored) {
        setSessionId(stored);
        setIsLoading(false);
        return;
      }

      // Tạo session mới từ backend
      try {
        const response = await fetch("/api/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: "Pomodoro Session",
            type: "pomodoro",
          }),
        });

        if (!response.ok) throw new Error("Failed to create session");

        const { id } = await response.json();
        localStorage.setItem("pomodoroSessionId", id);
        setSessionId(id);
      } catch (error) {
        console.error("Error creating session:", error);
        setSessionId("default-session-id");
      } finally {
        setIsLoading(false);
      }
    };

    getOrCreateSessionId();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-100">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-slate-300 border-t-slate-600 rounded-full mx-auto mb-4" />
          <p className="text-slate-600">Đang tải Pomodoro...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Thanh điều hướng */}
      <div className="fixed top-0 left-0 right-0 bg-white border-b border-slate-200 p-4 flex justify-between items-center">
        <h2 className="text-lg font-bold text-slate-800">
          Smart Learning Support
        </h2>

        <div className="flex gap-4">
          <button
            onClick={() => router.push("/dashboard")}
            className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg"
          >
            📊 Dashboard
          </button>
          <button
            onClick={() => router.push("/analytics")}
            className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg"
          >
            📈 Analytics
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="pt-16">
        <PomodoroTimer
          sessionId={sessionId}
          workMinutes={25}
          breakMinutes={5}
        />
      </div>

      {/* Footer - Thông tin hữu ích */}
      <div className="fixed bottom-4 left-4 right-4 mx-auto max-w-md p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
        <p className="font-semibold mb-2">💡 Mẹo:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>Đưa khuôn mặt vào frame camera để AI giám sát</li>
          <li>Khi xao nhãng được phát hiện, đồng hồ sẽ tự động dừng</li>
          <li>Tiếp tục tập trung để tiếp tục đếm ngược</li>
        </ul>
      </div>
    </div>
  );
}
