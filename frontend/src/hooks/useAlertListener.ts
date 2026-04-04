/**
 * useAlertListener Hook
 *
 * Lắng nghe tín hiệu cảnh báo xao nhãng từ Backend qua Websocket hoặc Supabase Realtime.
 *
 * Tính năng:
 * - Tự động dừng đồng hồ Pomodoro khi nhận "alert: start"
 * - Tự động tiếp tục khi nhận "alert: stop"
 * - Cập nhật trạng thái isDistracted để hiển thị chỉ báo UI
 * - Hỗ trợ Websocket và Supabase Realtime
 * - Tự động reconnect khi connection mất
 *
 * Cách sử dụng:
 * ```
 * const { isDistracted, alertStatus } = useAlertListener({
 *   sessionId: "abc123",
 *   pauseTimer: pauseTimer,
 *   resumeTimer: resumeTimer,
 *   useWebsocket: true, // hoặc false để dùng Supabase Realtime
 * });
 * ```
 */

import { useEffect, useState, useRef, useCallback } from "react";
import { createSupabaseClient } from "@/lib/supabase";
import { API_BASE, apiFetch } from "@/lib/api-client";

interface StreamTicketResponse {
  ticket: string;
  expires_in_sec: number;
}

interface AlertStreamMessage {
  type?: string;
  severity?: "critical" | "medium" | "soft";
  event_type?: string;
}

const DISTRACTION_EVENTS = new Set([
  "drowsiness",
  "bad_posture",
  "posture_deviation",
  "focus_offscreen",
  "phone_detected",
  "face_too_close",
]);

function wsBaseFromApiBase(apiBase: string): string {
  try {
    const url = new URL(apiBase);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = "/";
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return "ws://localhost:8000/";
  }
}

export interface UseAlertListenerOptions {
  /** ID của session hiện tại (để xác định user) */
  sessionId: string;

  /** Hàm dừng đồng hồ (callback từ component Pomodoro) */
  pauseTimer: () => void;

  /** Hàm tiếp tục đồng hồ (callback từ component Pomodoro) */
  resumeTimer: () => void;

  /** Dùng Websocket (true) hay Supabase Realtime (false)? Mặc định: true */
  useWebsocket?: boolean;

  /** URL backend cho Websocket (mặc định: ws://localhost:8000/api/v1/monitoring/alerts-stream) */
  websocketUrl?: string;

  /** Cho phép log debug? Mặc định: false */
  debug?: boolean;
}

export interface UseAlertListenerReturn {
  /** Đang bị giám sát/cảnh báo? */
  isDistracted: boolean;

  /** Trạng thái tín hiệu ("idle" | "monitoring" | "error") */
  alertStatus: "idle" | "monitoring" | "error";

  /** Timestamp lần cuối nhận tín hiệu */
  lastAlertAt: number | null;
}

/**
 * Hook để lắng nghe tín hiệu cảnh báo xao nhãng từ backend.
 *
 * @param options - Cấu hình hook
 * @returns Trạng thái cảnh báo và UI feedback
 */
export function useAlertListener(
  options: UseAlertListenerOptions,
): UseAlertListenerReturn {
  const {
    sessionId,
    pauseTimer,
    resumeTimer,
    useWebsocket = true,
    websocketUrl = "ws://localhost:8000/api/v1/monitoring/alerts-stream",
    debug = false,
  } = options;

  // ========================================================================
  // State
  // ========================================================================

  /** Đang trong trạng thái bị xao nhãng? */
  const [isDistracted, setIsDistracted] = useState(false);

  /** Trạng thái kết nối */
  const [alertStatus, setAlertStatus] = useState<
    "idle" | "monitoring" | "error"
  >("idle");

  /** Timestamp lần cuối nhận tín hiệu */
  const [lastAlertAt, setLastAlertAt] = useState<number | null>(null);

  // ========================================================================
  // Ref (để tránh re-create connection mỗi render)
  // ========================================================================

  /** Reference đến Websocket */
  const wsRef = useRef<WebSocket | null>(null);

  /** Reference đến Supabase realtime subscription */
  const realtimeSubRef = useRef<{ unsubscribe: () => void } | null>(null);

  /** Reference đến reconnect timeout */
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /** Reference đến timer tự clear cảnh báo khi không có alert mới */
  const autoClearTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /** Cho phép reconnect khi component còn mounted */
  const shouldReconnectRef = useRef(true);

  const log = useCallback(
    (msg: string, data?: unknown) => {
      if (debug) {
        console.debug(`[useAlertListener] ${msg}`, data || "");
      }
    },
    [debug],
  );

  // ========================================================================
  // Websocket Methods
  // ========================================================================

  /**
   * Xử lý tín hiệu cảnh báo từ backend.
   *
   * Payloads:
   * - { status: "start" } → Người dùng bắt đầu xao nhãng → dừng đồng hồ
   * - { status: "stop" } → Người dùng tập trung lại → tiếp tục đồng hồ
   */
  const handleAlertSignal = useCallback(
    (status: "start" | "stop", clearAfterMs?: number) => {
      log("Handling alert signal", { status, clearAfterMs });
      setLastAlertAt(Date.now());

      if (autoClearTimeoutRef.current) {
        clearTimeout(autoClearTimeoutRef.current);
        autoClearTimeoutRef.current = null;
      }

      if (status === "start") {
        // ❌ Xao nhãng → Dừng đồng hồ
        setIsDistracted(true);
        pauseTimer();
        log("Pausing timer due to distraction alert");

        if (clearAfterMs && clearAfterMs > 0) {
          autoClearTimeoutRef.current = setTimeout(() => {
            setIsDistracted(false);
            resumeTimer();
            log("Auto-resume timer after quiet period");
          }, clearAfterMs);
        }
      } else if (status === "stop") {
        // ✅ Tập trung → Tiếp tục đồng hồ
        setIsDistracted(false);
        resumeTimer();
        log("Resuming timer - user is focused");
      }
    },
    [pauseTimer, resumeTimer, log],
  );

  /**
   * Kết nối đến Websocket để lắng nghe cảnh báo.
   */
  const connectWebsocket = useCallback(async () => {
    try {
      const ticketResp = await apiFetch<StreamTicketResponse>(
        "/api/v1/monitoring/stream-ticket",
        { method: "POST" },
      );

      const streamUrl = websocketUrl
        ? new URL(websocketUrl)
        : new URL(
            "/api/v1/monitoring/alerts-stream",
            wsBaseFromApiBase(API_BASE),
          );

      log("Connecting to Websocket", { url: streamUrl.toString() });

      streamUrl.searchParams.set("ticket", ticketResp.ticket);
      streamUrl.searchParams.set("session_id", sessionId);

      // Tạo Websocket connection
      const ws = new WebSocket(streamUrl.toString());
      wsRef.current = ws;

      ws.onopen = () => {
        log("Websocket connected");
        setAlertStatus("monitoring");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as AlertStreamMessage;

          if (data?.type === "alert") {
            const eventType = (data.event_type || "").toLowerCase();
            if (DISTRACTION_EVENTS.has(eventType)) {
              const clearAfterMs =
                data.severity === "critical" ? 10_000 : 6_000;
              handleAlertSignal("start", clearAfterMs);
            }
          }
        } catch (e) {
          log("Failed to parse websocket message", e);
        }
      };

      ws.onerror = (error) => {
        log("Websocket error", error);
        setAlertStatus("error");
      };

      ws.onclose = () => {
        log("Websocket closed, will reconnect in 5s");
        setAlertStatus("idle");
        wsRef.current = null;

        // Reconnect sau 5 giây
        if (shouldReconnectRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebsocket();
          }, 5000);
        }
      };
    } catch (e) {
      log("Failed to connect Websocket", e);
      setAlertStatus("error");

      if (shouldReconnectRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebsocket();
        }, 5000);
      }
    }
  }, [sessionId, websocketUrl, handleAlertSignal, log]);

  // ========================================================================
  // Supabase Realtime Methods
  // ========================================================================

  /**
   * Kết nối đến Supabase Realtime để lắng nghe cảnh báo.
   *
   * Giả định có bảng "alerts" với schema:
   * - id (uuid, pk)
   * - user_id (uuid)
   * - session_id (uuid)
   * - status (enum: 'start' | 'stop')
   * - created_at (timestamp)
   */
  const connectSupabaseRealtime = useCallback(async () => {
    try {
      log("Connecting to Supabase Realtime");

      const supabase = createSupabaseClient();

      // Subscribe vào changes trong bảng alerts cho session này
      const subscription = supabase
        .channel(`alerts:session_id.eq.${sessionId}`)
        .on(
          "postgres_changes",
          {
            event: "INSERT",
            schema: "public",
            table: "alerts",
            filter: `session_id=eq.${sessionId}`,
          },
          (payload) => {
            const newRecord = payload.new as Record<string, unknown>;
            const status = newRecord?.status;
            if (status === "start" || status === "stop") {
              handleAlertSignal(status);
            }
          },
        )
        .subscribe((status) => {
          if (status === "SUBSCRIBED") {
            log("Supabase Realtime subscribed");
            setAlertStatus("monitoring");
          } else if (status === "CHANNEL_ERROR") {
            log("Supabase Realtime error");
            setAlertStatus("error");
          } else if (status === "CLOSED") {
            log("Supabase Realtime closed");
            setAlertStatus("idle");
          }
        });

      realtimeSubRef.current = subscription;
    } catch (e) {
      log("Failed to connect Supabase Realtime", e);
      setAlertStatus("error");
    }
  }, [sessionId, handleAlertSignal, log]);

  // ========================================================================
  // Effect: Setup Connection
  // ========================================================================

  useEffect(() => {
    shouldReconnectRef.current = true;
    log("useAlertListener mounted", { sessionId, useWebsocket });

    if (!sessionId) {
      log("No session ID provided, skipping connection");
      return;
    }

    if (useWebsocket) {
      connectWebsocket();
    } else {
      connectSupabaseRealtime();
    }

    return () => {
      log("useAlertListener cleanup");
      shouldReconnectRef.current = false;

      // Đóng Websocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      // Unsubscribe Supabase Realtime
      if (realtimeSubRef.current) {
        realtimeSubRef.current.unsubscribe();
        realtimeSubRef.current = null;
      }

      // Clear reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      if (autoClearTimeoutRef.current) {
        clearTimeout(autoClearTimeoutRef.current);
        autoClearTimeoutRef.current = null;
      }
    };
  }, [sessionId, useWebsocket, connectWebsocket, connectSupabaseRealtime, log]);

  return {
    isDistracted,
    alertStatus,
    lastAlertAt,
  };
}
