/**
 * Telemetry client for submitting camera FPS metrics to backend.
 * NOTE: Live UI metrics now use WebSocket stream from CameraWidget as source of truth.
 * This module is kept for diagnostic or future background reporting flows only.
 */

export interface CameraTelemetry {
  user_id: string;
  timestamp: string;
  python_fps: number | null;
  web_fps: number | null;
  frame_latency_ms: number | null;
  camera_resolution: string;
  processing_resolution: string;
  notes?: string;
}

/**
 * Submit camera telemetry metrics to backend.
 * Called approximately every 5 seconds during active monitoring.
 */
export async function postCameraTelemetry({
  python_fps,
  web_fps,
  frame_latency_ms,
  camera_resolution = "640x480",
  processing_resolution = "256x192",
  notes,
}: {
  python_fps?: number | null;
  web_fps?: number | null;
  frame_latency_ms?: number | null;
  camera_resolution?: string;
  processing_resolution?: string;
  notes?: string;
}): Promise<void> {
  try {
    const response = await fetch("/api/v1/monitoring/telemetry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        python_fps,
        web_fps,
        frame_latency_ms,
        camera_resolution,
        processing_resolution,
        notes,
      }),
    });

    if (!response.ok) {
      console.warn("Telemetry POST failed:", response.statusText);
    }
  } catch (error) {
    console.error("Telemetry client error:", error);
  }
}

/**
 * Fetch latest camera telemetry from backend for diagnostics.
 */
export async function getCameraTelemetry(): Promise<CameraTelemetry | null> {
  try {
    const response = await fetch("/api/v1/monitoring/telemetry");
    if (!response.ok) return null;
    return response.json();
  } catch (error) {
    console.error("Telemetry fetch error:", error);
    return null;
  }
}
