"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE, getApiAccessToken } from "@/lib/api-client";

interface CameraWidgetProps {
  className?: string;
}

export function CameraWidget({ className }: CameraWidgetProps) {
  const objectUrlRef = useRef<string | null>(null);
  const frameCounterRef = useRef(0);
  const fpsWindowStartRef = useRef<number>(Date.now());
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [webFps, setWebFps] = useState(0);
  const [pythonFps, setPythonFps] = useState({
    main: 0,
    camera: 0,
    ai: 0,
  });

  useEffect(() => {
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    async function loadSnapshot() {
      try {
        const token = await getApiAccessToken();
        const res = await fetch(
          `${API_BASE}/api/v1/monitoring/snapshot?t=${Date.now()}`,
          {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            credentials: "include",
            cache: "no-store",
          },
        );

        if (cancelled) return;

        if (res.status === 404) {
          setReady(false);
          setError(null);
          timeoutId = setTimeout(() => void loadSnapshot(), 220);
          return;
        }

        if (!res.ok) {
          throw new Error(`Snapshot request failed: ${res.status}`);
        }

        const parseFps = (name: string) => {
          const raw = res.headers.get(name);
          const n = raw ? Number(raw) : 0;
          return Number.isFinite(n) ? n : 0;
        };
        setPythonFps({
          main: parseFps("X-Python-Fps-Main"),
          camera: parseFps("X-Python-Fps-Camera"),
          ai: parseFps("X-Python-Fps-Ai"),
        });

        const blob = await res.blob();
        if (cancelled) {
          return;
        }

        const nextUrl = URL.createObjectURL(blob);
        if (objectUrlRef.current) {
          URL.revokeObjectURL(objectUrlRef.current);
        }
        objectUrlRef.current = nextUrl;
        setImageUrl(nextUrl);

        frameCounterRef.current += 1;
        const now = Date.now();
        const elapsed = now - fpsWindowStartRef.current;
        if (elapsed >= 1000) {
          const fps = (frameCounterRef.current * 1000) / elapsed;
          setWebFps(Number(fps.toFixed(1)));
          frameCounterRef.current = 0;
          fpsWindowStartRef.current = now;
        }

        setReady(true);
        setError(null);
        timeoutId = setTimeout(() => void loadSnapshot(), 100);
      } catch (err) {
        if (!cancelled) {
          setReady(false);
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load monitoring snapshot.",
          );
          timeoutId = setTimeout(() => void loadSnapshot(), 600);
        }
      }
    }

    void loadSnapshot();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
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
        className={`rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center p-3 text-xs text-gray-500 text-center ${className ?? ""}`}
        style={{ minHeight: 120 }}
      >
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div
      className={`relative rounded-lg overflow-hidden bg-black ${className ?? ""}`}
      style={{ minHeight: 120 }}
    >
      {ready && (
        <div className="absolute top-2 right-2 z-10 rounded bg-black/65 px-2 py-1 text-[10px] text-white leading-tight">
          <p>Web FPS: {webFps}</p>
          <p>
            Py FPS M/C/A: {pythonFps.main}/{pythonFps.camera}/{pythonFps.ai}
          </p>
        </div>
      )}
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80 text-center px-3">
          <span className="text-xs text-gray-300 animate-pulse">
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
            style={{ opacity: ready ? 1 : 0 }}
          />
        </>
      )}
    </div>
  );
}
