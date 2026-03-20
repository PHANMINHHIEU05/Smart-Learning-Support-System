"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE, ApiError, apiFetch, getApiAccessToken } from "@/lib/api-client";

export interface CameraStreamMetrics {
  source: "websocket";
  pythonMainFps: number;
  pythonCameraFps: number;
  pythonAiFps: number;
  webFps: number;
  frameLatencyMs: number | null;
}

interface CameraWidgetProps {
  className?: string;
  onMetrics?: (metrics: CameraStreamMetrics) => void;
}

function normalizeApiBaseUrl(): string {
  const raw = (API_BASE ?? "").trim();
  if (!raw) {
    if (typeof window !== "undefined") return window.location.origin;
    return "http://localhost:8000";
  }

  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw;
  }

  if (raw.startsWith("//")) {
    if (typeof window !== "undefined") {
      return `${window.location.protocol}${raw}`;
    }
    return `http:${raw}`;
  }

  if (raw.startsWith("/")) {
    if (typeof window !== "undefined") {
      return `${window.location.origin}${raw}`;
    }
    return `http://localhost:8000${raw}`;
  }

  // Handle host:port values like "localhost:8000"
  if (/^[a-zA-Z0-9.-]+(?::\d+)?$/.test(raw)) {
    if (typeof window !== "undefined") {
      return `${window.location.protocol}//${raw}`;
    }
    return `http://${raw}`;
  }

  return raw;
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message.trim();
  }
  if (typeof error === "string" && error.trim().length > 0) return error.trim();
  if (
    error &&
    typeof error === "object" &&
    "message" in error &&
    typeof (error as { message?: unknown }).message === "string"
  ) {
    const message = (error as { message: string }).message.trim();
    if (message.length > 0) return message;
  }
  return fallback;
}

function redactWsUrl(url: string): string {
  try {
    const parsed = new URL(url);
    if (parsed.searchParams.has("token")) {
      parsed.searchParams.set("token", "[redacted]");
    }
    if (parsed.searchParams.has("ticket")) {
      parsed.searchParams.set("ticket", "[redacted]");
    }
    return parsed.toString();
  } catch {
    return url;
  }
}

async function isBackendReachable(baseUrl: string): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2500);
    const response = await fetch(`${baseUrl}/health`, {
      method: "GET",
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timeout);
    return response.ok;
  } catch {
    return false;
  }
}

export function CameraWidget({ className, onMetrics }: CameraWidgetProps) {
  const objectUrlRef = useRef<string | null>(null);
  const websocketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fallbackPollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fallbackModeRef = useRef(false);
  const fallbackEtagRef = useRef<string | null>(null);
  const frameCounterRef = useRef(0);
  const fpsWindowStartRef = useRef<number>(Date.now());
  const lastFrameAtRef = useRef<number | null>(null);
  const lastMessageAtRef = useRef<number>(Date.now());
  const lastPublishedMetricsRef = useRef<CameraStreamMetrics>({
    source: "websocket",
    pythonMainFps: 0,
    pythonCameraFps: 0,
    pythonAiFps: 0,
    webFps: 0,
    frameLatencyMs: null,
  });
  const onMetricsRef = useRef(onMetrics);
  const webFpsRef = useRef(0);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [webFps, setWebFps] = useState(0);
  const [pythonFps, setPythonFps] = useState({
    main: 0,
    camera: 0,
    ai: 0,
  });
  const [transportMode, setTransportMode] = useState<
    "websocket" | "snapshot_fallback"
  >("websocket");

  useEffect(() => {
    onMetricsRef.current = onMetrics;
  }, [onMetrics]);

  useEffect(() => {
    let cancelled = false;
    let reconnectAttempt = 0;
    let lastWsUrl = "";
    const RECONNECT_BASE_MS = 700;
    const RECONNECT_MAX_MS = 5000;
    const STALE_CONNECTION_MS = 7000;
    const FALLBACK_AFTER_ATTEMPTS = 3;
    const SNAPSHOT_FALLBACK_INTERVAL_MS = 250;

    const publishMetrics = (metrics: Partial<CameraStreamMetrics>) => {
      const merged: CameraStreamMetrics = {
        ...lastPublishedMetricsRef.current,
        ...metrics,
        source: "websocket",
      };
      lastPublishedMetricsRef.current = merged;
      onMetricsRef.current?.(merged);
    };

    const buildWebSocketUrl = (auth: { ticket: string }): string => {
      const baseUrl = normalizeApiBaseUrl();
      const url = new URL(baseUrl);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      url.pathname = "/api/v1/monitoring/stream";
      url.search = "";
      url.searchParams.set("ticket", auth.ticket);
      return url.toString();
    };

    const scheduleReconnect = (
      delayMs: number,
      forceRefreshToken = false,
    ) => {
      if (cancelled) return;
      if (fallbackModeRef.current) return;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(
        () => void connect(forceRefreshToken),
        delayMs,
      );
    };

    const updateFpsWindow = (): number => {
      frameCounterRef.current += 1;
      const now = Date.now();
      const elapsed = now - fpsWindowStartRef.current;
      if (elapsed >= 1000) {
        const fps = (frameCounterRef.current * 1000) / elapsed;
        const rounded = Number(fps.toFixed(1));
        webFpsRef.current = rounded;
        setWebFps(rounded);
        frameCounterRef.current = 0;
        fpsWindowStartRef.current = now;
        return rounded;
      }
      return webFpsRef.current;
    };

    const handleFrameBlob = (blob: Blob) => {
      const now = Date.now();
      const frameLatencyMs =
        lastFrameAtRef.current !== null ? now - lastFrameAtRef.current : null;
      lastFrameAtRef.current = now;

      const nextUrl = URL.createObjectURL(blob);
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
      }
      objectUrlRef.current = nextUrl;
      setImageUrl(nextUrl);
      setReady(true);
      setError(null);
      const currentWebFps = updateFpsWindow();
      publishMetrics({
        webFps: currentWebFps,
        frameLatencyMs,
      });
    };

    const stopSnapshotFallback = () => {
      if (fallbackPollingRef.current) {
        clearInterval(fallbackPollingRef.current);
        fallbackPollingRef.current = null;
      }
      fallbackEtagRef.current = null;
      fallbackModeRef.current = false;
      setTransportMode("websocket");
    };

    const startSnapshotFallback = () => {
      if (cancelled) return;
      if (fallbackModeRef.current) return;
      fallbackModeRef.current = true;
      setTransportMode("snapshot_fallback");
      setError("WebSocket unavailable. Switching to fallback snapshot mode.");

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (heartbeatTimerRef.current) {
        clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
      if (websocketRef.current) {
        websocketRef.current.close();
        websocketRef.current = null;
      }

      const pollSnapshot = async () => {
        try {
          const baseUrl = normalizeApiBaseUrl();
          const token = await getApiAccessToken();
          if (!token) {
            setReady(false);
            setError("Missing auth token for fallback snapshot mode.");
            return;
          }

          const headers: Record<string, string> = {
            Authorization: `Bearer ${token}`,
            "Cache-Control": "no-cache",
          };
          if (fallbackEtagRef.current) {
            headers["If-None-Match"] = fallbackEtagRef.current;
          }

          const response = await fetch(`${baseUrl}/api/v1/monitoring/snapshot`, {
            method: "GET",
            headers,
            cache: "no-store",
          });

          if (response.status === 304) {
            return;
          }

          if (response.status === 404) {
            setReady(false);
            setError("Waiting for monitoring snapshot...");
            return;
          }

          if (response.status === 401 || response.status === 403) {
            setReady(false);
            setError("Session expired. Please sign out and sign in again.");
            return;
          }

          if (response.status >= 500) {
            setReady(false);
            setError("Snapshot backend is warming up. Retrying...");
            return;
          }

          if (!response.ok) {
            setReady(false);
            setError(`Fallback snapshot request failed (HTTP ${response.status}).`);
            return;
          }

          const etag = response.headers.get("ETag");
          if (etag) fallbackEtagRef.current = etag;

          const parseHeaderNumber = (value: string | null) => {
            const n = Number(value ?? "0");
            return Number.isFinite(n) ? n : 0;
          };
          const pythonMain = parseHeaderNumber(
            response.headers.get("X-Python-Fps-Main"),
          );
          const pythonCamera = parseHeaderNumber(
            response.headers.get("X-Python-Fps-Camera"),
          );
          const pythonAi = parseHeaderNumber(response.headers.get("X-Python-Fps-Ai"));

          setPythonFps({
            main: pythonMain,
            camera: pythonCamera,
            ai: pythonAi,
          });
          publishMetrics({
            pythonMainFps: pythonMain,
            pythonCameraFps: pythonCamera,
            pythonAiFps: pythonAi,
          });

          const blob = await response.blob();
          handleFrameBlob(blob);
        } catch (fallbackError) {
          setReady(false);
          setError(
            extractErrorMessage(
              fallbackError,
              "Fallback snapshot polling failed.",
            ),
          );
        }
      };

      void pollSnapshot();
      fallbackPollingRef.current = setInterval(
        () => void pollSnapshot(),
        SNAPSHOT_FALLBACK_INTERVAL_MS,
      );
    };

    const handleControlMessage = (raw: string) => {
      try {
        const data = JSON.parse(raw) as Record<string, unknown>;
        if (data.type === "metrics") {
          const parseNumber = (value: unknown) => {
            const n = Number(value);
            return Number.isFinite(n) ? n : 0;
          };
          setPythonFps({
            main: parseNumber(data.main_fps),
            camera: parseNumber(data.camera_fps),
            ai: parseNumber(data.ai_fps),
          });
          publishMetrics({
            pythonMainFps: parseNumber(data.main_fps),
            pythonCameraFps: parseNumber(data.camera_fps),
            pythonAiFps: parseNumber(data.ai_fps),
          });
          return;
        }

        if (data.type === "status") {
          if (data.ready === false) {
            setReady(false);
          }
          return;
        }

        if (data.type === "error") {
          setError(
            typeof data.message === "string"
              ? data.message
              : "Monitoring stream error.",
          );
        }
      } catch {
        setError("Monitoring stream payload parsing failed.");
      }
    };

    async function connect(forceRefreshToken = false) {
      let resolvedApiBase = normalizeApiBaseUrl();
      let attemptedWsUrl = "";
      try {
        const token = await getApiAccessToken({ forceRefresh: forceRefreshToken });
        if (cancelled) return;

        if (!token) {
          setReady(false);
          setError("Missing auth token for monitoring stream.");
          scheduleReconnect(RECONNECT_BASE_MS, true);
          return;
        }

        let streamTicket = "";
        try {
          const ticketResponse = await apiFetch<{
            ticket: string;
            expires_in_sec: number;
          }>("/api/v1/monitoring/stream-ticket", {
            method: "POST",
          });
          streamTicket = ticketResponse.ticket;
          if (!streamTicket) {
            setReady(false);
            setError("Monitoring stream ticket response missing ticket.");
            scheduleReconnect(RECONNECT_BASE_MS, true);
            return;
          }
        } catch (ticketError) {
          setReady(false);
          if (ticketError instanceof ApiError) {
            if (ticketError.status === 404) {
              setError(
                "Backend is missing /api/v1/monitoring/stream-ticket. Restart backend with latest code.",
              );
            } else if (ticketError.status === 401 || ticketError.status === 403) {
              setError("Session expired. Please sign out and sign in again.");
            } else {
              setError(
                `Failed to request monitoring stream ticket (HTTP ${ticketError.status}).`,
              );
            }
          } else {
            const ticketDetail = extractErrorMessage(
              ticketError,
              "Failed to request monitoring stream ticket.",
            );
            setError(ticketDetail);
          }
          scheduleReconnect(RECONNECT_BASE_MS, true);
          return;
        }

        let wsUrl = "";
        try {
          resolvedApiBase = normalizeApiBaseUrl();
          wsUrl = buildWebSocketUrl({ ticket: streamTicket });
          attemptedWsUrl = wsUrl;
        } catch {
          setReady(false);
          setError(
            `Invalid API URL configuration for monitoring stream. [api=${resolvedApiBase}]`,
          );
          scheduleReconnect(RECONNECT_BASE_MS, true);
          return;
        }

        if (
          typeof window !== "undefined" &&
          window.location.protocol === "https:" &&
          wsUrl.startsWith("ws://")
        ) {
          setReady(false);
          setError(
            "Cannot open insecure ws:// stream from an https page. Configure NEXT_PUBLIC_API_URL with https.",
          );
          scheduleReconnect(RECONNECT_MAX_MS, true);
          return;
        }

        lastWsUrl = wsUrl;
        const ws = new WebSocket(wsUrl);
        ws.binaryType = "blob";
        websocketRef.current = ws;

        ws.onopen = () => {
          if (cancelled || websocketRef.current !== ws) return;
          reconnectAttempt = 0;
          lastMessageAtRef.current = Date.now();
          stopSnapshotFallback();
          setError(null);

          if (heartbeatTimerRef.current) {
            clearInterval(heartbeatTimerRef.current);
          }
          heartbeatTimerRef.current = setInterval(() => {
            if (cancelled || websocketRef.current !== ws) return;
            const staleFor = Date.now() - lastMessageAtRef.current;
            if (staleFor >= STALE_CONNECTION_MS) {
              websocketRef.current?.close();
            }
          }, 1500);
        };

        ws.onmessage = (event: MessageEvent) => {
          if (cancelled || websocketRef.current !== ws) return;
          lastMessageAtRef.current = Date.now();
          if (typeof event.data === "string") {
            handleControlMessage(event.data);
            return;
          }
          if (event.data instanceof Blob) {
            handleFrameBlob(event.data);
          }
        };

        ws.onerror = () => {
          if (cancelled || websocketRef.current !== ws) return;
          const wsContext = lastWsUrl ? ` [ws=${redactWsUrl(lastWsUrl)}]` : "";
          setError(`WebSocket camera stream interrupted.${wsContext}`);
        };

        ws.onclose = (event: CloseEvent) => {
          if (cancelled || websocketRef.current !== ws) return;
          if (heartbeatTimerRef.current) {
            clearInterval(heartbeatTimerRef.current);
            heartbeatTimerRef.current = null;
          }
          websocketRef.current = null;
          setReady(false);
          const unauthorized = event.code === 4401;
          const wsContext = lastWsUrl
            ? ` [ws=${redactWsUrl(lastWsUrl)}]`
            : "";
          if (unauthorized) {
            setError("Monitoring stream unauthorized. Please sign in again.");
          } else if (event.code === 1006) {
            void (async () => {
              const baseUrl = normalizeApiBaseUrl();
              const reachable = await isBackendReachable(baseUrl);
              if (!reachable) {
                setError(
                  `Cannot reach backend at ${baseUrl}. Start backend server and retry.`,
                );
                return;
              }
              setError(
                `Monitoring stream dropped unexpectedly.${wsContext}`,
              );
            })();
          } else if (event.reason) {
            setError(`Monitoring stream closed: ${event.reason}${wsContext}`);
          }
          const jitter = Math.floor(Math.random() * 180);
          const backoff = Math.min(
            RECONNECT_BASE_MS * 2 ** Math.min(reconnectAttempt, 4) + jitter,
            RECONNECT_MAX_MS,
          );
          reconnectAttempt += 1;
          if (reconnectAttempt >= FALLBACK_AFTER_ATTEMPTS) {
            startSnapshotFallback();
            return;
          }
          scheduleReconnect(backoff, unauthorized);
        };
      } catch (err) {
        if (cancelled) return;
        setReady(false);
        const errorName =
          err && typeof err === "object" && "name" in err
            ? String((err as { name?: unknown }).name ?? "")
            : "";
        const detail = extractErrorMessage(
          err,
          "Failed to initialize monitoring stream.",
        ).trim();
        const safeDetail =
          detail.length > 0 ? detail : "Failed to initialize monitoring stream.";
        if (errorName === "SecurityError") {
          setError(
            "Monitoring stream blocked by browser security policy. Check protocol mismatch (https page vs ws backend).",
          );
        } else {
          const baseUrl = resolvedApiBase;
          const reachable = await isBackendReachable(baseUrl);
          if (!reachable) {
            setError(
              `Cannot reach backend at ${baseUrl}. Start backend server and retry.`,
            );
          } else {
            if (attemptedWsUrl) {
              setError(
                `${safeDetail} [api=${baseUrl}] [ws=${redactWsUrl(attemptedWsUrl)}]`,
              );
            } else {
              setError(`${safeDetail} [api=${baseUrl}]`);
            }
          }
        }
        const backoff = Math.min(
          RECONNECT_BASE_MS * 2 ** Math.min(reconnectAttempt, 3),
          RECONNECT_MAX_MS,
        );
        reconnectAttempt += 1;
        if (reconnectAttempt >= FALLBACK_AFTER_ATTEMPTS) {
          startSnapshotFallback();
          return;
        }
        scheduleReconnect(backoff, true);
      }
    }

    void connect();

    return () => {
      cancelled = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (heartbeatTimerRef.current) {
        clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
      if (fallbackPollingRef.current) {
        clearInterval(fallbackPollingRef.current);
        fallbackPollingRef.current = null;
      }
      if (websocketRef.current) {
        websocketRef.current.close();
        websocketRef.current = null;
      }
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
      setReady(false);
    };
  }, []);

  if (error) {
    return (
      <div
        className={`surface-card flex items-center justify-center p-3 text-center text-xs text-rose-700 ${className ?? ""}`}
        style={{ minHeight: 120 }}
      >
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-slate-200/80 bg-slate-900 ${className ?? ""}`}
      style={{ minHeight: 120 }}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-cyan-300/10 via-transparent to-amber-200/10" />
      {ready && (
        <div className="absolute right-2 top-2 z-10 rounded-lg border border-white/20 bg-slate-900/72 px-2 py-1 text-[10px] leading-tight text-cyan-100 backdrop-blur-sm">
          <p>
            Mode: {transportMode === "websocket" ? "WebSocket" : "Snapshot fallback"}
          </p>
          <p>Web FPS: {webFps}</p>
          <p>
            Py FPS M/C/A: {pythonFps.main}/{pythonFps.camera}/{pythonFps.ai}
          </p>
        </div>
      )}
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 px-3 text-center">
          <span className="animate-pulse text-xs text-cyan-100">
            Waiting for Python monitoring frame…
          </span>
        </div>
      )}
      {imageUrl && (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt="Processed monitoring camera feed"
            className="w-full h-auto block"
            decoding="async"
            loading="eager"
            style={{
              opacity: ready ? 1 : 0,
              filter: "brightness(1.2) contrast(1.08) saturate(1.1)",
            }}
          />
        </>
      )}
    </div>
  );
}
