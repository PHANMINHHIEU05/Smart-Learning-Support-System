"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE, apiFetch } from "@/lib/api-client";
import {
  postDetectFrame,
  type DetectResponse,
} from "@/lib/monitoring/browser-detect-client";

export interface CameraStreamMetrics {
  source: "detect_api";
  pythonMainFps: number;
  pythonCameraFps: number;
  pythonAiFps: number;
  webFps: number;
  frameLatencyMs: number | null;
}

interface CameraWidgetProps {
  sessionId: string | null;
  className?: string;
  onMetrics?: (metrics: CameraStreamMetrics) => void;
}

function wsBaseFromApiBase(apiBase: string): string {
  const parsed = new URL(apiBase);
  parsed.protocol = parsed.protocol === "https:" ? "wss:" : "ws:";
  return parsed.toString();
}

export function CameraWidget({
  sessionId,
  className,
  onMetrics,
}: CameraWidgetProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const drawCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const detectTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const alertWsRef = useRef<WebSocket | null>(null);
  const frameSeqRef = useRef(0);
  const detectBusyRef = useRef(false);
  const frameCounterRef = useRef(0);
  const fpsWindowStartRef = useRef<number>(Date.now());
  const lastDetectAtRef = useRef<number | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [latest, setLatest] = useState<DetectResponse | null>(null);

  const statusLabel = useMemo(() => {
    if (!latest) return "Warming up";
    if (!latest.ready) return "Initializing AI";
    return "Live";
  }, [latest]);

  useEffect(() => {
    let active = true;

    const clearResources = () => {
      if (detectTimerRef.current) {
        clearInterval(detectTimerRef.current);
        detectTimerRef.current = null;
      }
      if (alertWsRef.current) {
        alertWsRef.current.close();
        alertWsRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
      detectBusyRef.current = false;
      frameSeqRef.current = 0;
      frameCounterRef.current = 0;
      fpsWindowStartRef.current = Date.now();
      lastDetectAtRef.current = null;
    };

    const drawOverlay = (payload: DetectResponse) => {
      const canvas = drawCanvasRef.current;
      const video = videoRef.current;
      if (!canvas || !video) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const box = payload.overlay.face_bbox;
      if (box) {
        ctx.strokeStyle = "#22c55e";
        ctx.lineWidth = 2;
        ctx.strokeRect(box.x, box.y, box.w, box.h);
      }

      for (const p of payload.overlay.pose_points ?? []) {
        ctx.beginPath();
        ctx.arc(p[0], p[1], 2, 0, Math.PI * 2);
        ctx.fillStyle = "#38bdf8";
        ctx.fill();
      }

      for (const label of payload.overlay.labels ?? []) {
        const severity = label.severity ?? "soft";
        ctx.fillStyle =
          severity === "critical"
            ? "#ef4444"
            : severity === "medium"
              ? "#f59e0b"
              : "#ffffff";
        ctx.font = "14px sans-serif";
        ctx.fillText(label.text, label.x, label.y);
      }
    };

    const publishMetrics = (payload: DetectResponse) => {
      const now = Date.now();
      frameCounterRef.current += 1;
      const elapsed = now - fpsWindowStartRef.current;
      let webFps = 0;
      if (elapsed >= 1000) {
        webFps = Number(
          ((frameCounterRef.current * 1000) / elapsed).toFixed(1),
        );
        frameCounterRef.current = 0;
        fpsWindowStartRef.current = now;
      }

      const frameLatencyMs =
        lastDetectAtRef.current !== null ? now - lastDetectAtRef.current : null;
      lastDetectAtRef.current = now;

      const pyFps = Number(payload.perf.server_ai_fps || 0);
      onMetrics?.({
        source: "detect_api",
        pythonMainFps: pyFps,
        pythonCameraFps: pyFps,
        pythonAiFps: pyFps,
        webFps,
        frameLatencyMs,
      });
    };

    const openAlertSocket = async (sid: string) => {
      try {
        const ticket = await apiFetch<{ ticket: string }>(
          "/api/v1/monitoring/stream-ticket",
          { method: "POST" },
        );

        const wsBase = wsBaseFromApiBase(API_BASE);
        const wsUrl = new URL("/api/v1/monitoring/alerts-stream", wsBase);
        wsUrl.searchParams.set("ticket", ticket.ticket);
        wsUrl.searchParams.set("session_id", sid);

        const ws = new WebSocket(wsUrl.toString());
        alertWsRef.current = ws;

        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data as string);
            if (msg?.type === "alert") {
              // Alerts are still rendered by timer polling path in this phase.
              // This socket is enabled for live push and future UI wiring.
              // eslint-disable-next-line no-console
              console.debug("alert-stream", msg);
            }
          } catch {
            // ignore malformed payloads
          }
        };
      } catch {
        // Non-fatal. Detect flow can still run without live alert stream.
      }
    };

    const startDetectLoop = (sid: string) => {
      detectTimerRef.current = setInterval(async () => {
        if (!active || detectBusyRef.current) return;
        const video = videoRef.current;
        const capture = captureCanvasRef.current;
        if (
          !video ||
          !capture ||
          video.videoWidth === 0 ||
          video.videoHeight === 0
        ) {
          return;
        }

        detectBusyRef.current = true;
        try {
          const ctx = capture.getContext("2d");
          if (!ctx) return;

          capture.width = 640;
          capture.height = 360;
          ctx.drawImage(video, 0, 0, capture.width, capture.height);

          const blob = await new Promise<Blob | null>((resolve) =>
            capture.toBlob((b) => resolve(b), "image/jpeg", 0.68),
          );
          if (!blob) return;

          frameSeqRef.current += 1;
          const detected = await postDetectFrame({
            blob,
            sessionId: sid,
            clientTsMs: Date.now(),
            frameSeq: frameSeqRef.current,
          });

          if (!active) return;
          setLatest(detected);
          drawOverlay(detected);
          publishMetrics(detected);
          setError(null);
        } catch (e) {
          if (!active) return;
          const message = e instanceof Error ? e.message : "Detect loop error";
          setError(message);
        } finally {
          detectBusyRef.current = false;
        }
      }, 500);
    };

    const start = async () => {
      if (!sessionId) {
        setLatest(null);
        setError("Waiting for active session to start camera...");
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 },
        },
        audio: false,
      });

      if (!active) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }

      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) return;
      video.srcObject = stream;
      await video.play();

      await openAlertSocket(sessionId);
      startDetectLoop(sessionId);
      setError(null);
    };

    void start().catch((e) => {
      if (!active) return;
      setError(e instanceof Error ? e.message : "Camera init failed");
    });

    return () => {
      active = false;
      clearResources();
    };
  }, [onMetrics, sessionId]);

  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-slate-200/80 bg-slate-950 ${className ?? ""}`}
      style={{ minHeight: 180 }}
    >
      <div className="camera-layer relative">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="w-full h-auto block"
        />
        <canvas
          ref={drawCanvasRef}
          className="absolute inset-0 h-full w-full"
        />
        <canvas ref={captureCanvasRef} style={{ display: "none" }} />
      </div>

      <div className="pointer-events-none absolute right-2 top-2 z-10 rounded-lg border border-white/20 bg-slate-900/72 px-2 py-1 text-[10px] leading-tight text-cyan-100 backdrop-blur-sm">
        <p>Status: {statusLabel}</p>
        <p>Detect: {latest?.perf?.detect_ms ?? 0} ms</p>
        <p>AI FPS: {latest?.perf?.server_ai_fps ?? 0}</p>
      </div>

      {error ? (
        <div className="absolute bottom-2 left-2 right-2 rounded bg-rose-500/90 px-2 py-1 text-xs text-white">
          {error}
        </div>
      ) : null}
    </div>
  );
}
