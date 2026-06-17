import { getApiAccessToken, getApiBaseForPath } from "@/lib/api-client";

export interface DetectResponse {
  ready: boolean;
  is_calibrating?: boolean;
  calibration_progress?: number;
  server_ts_ms: number;
  session_id: string;
  frame_seq?: number;
  focus_score: number;
  confidence: number;
  state_flags: {
    is_drowsy: boolean;
    is_bad_posture: boolean;
    is_distracted: boolean;
    is_using_phone: boolean;
    is_too_close?: boolean;
    is_too_far?: boolean;
  };
  overlay: {
    face_bbox?: { x: number; y: number; w: number; h: number };
    pose_points: Array<[number, number]>;
    gaze_vector?: { x1: number; y1: number; x2: number; y2: number };
    labels: Array<{ text: string; x: number; y: number; severity: string }>;
  };
  perf: {
    detect_ms: number;
    server_ai_fps: number;
  };
  derived_event?: string | null;
  posture_error_code?: string | null;
  posture_current_error_code?: string | null;
  posture_error_message?: string | null;
  posture_current_error_message?: string | null;
  intervention_state: {
    escalation_level: "none" | "warning" | "paused";
    pause_reason: "distraction" | "leave_seat" | null;
    resume_countdown_sec: number | null;
    last_update_ts: string;
  };
}

export async function postDetectFrame(input: {
  blob: Blob;
  sessionId: string;
  clientTsMs: number;
  frameSeq: number;
}): Promise<DetectResponse> {
  const token = await getApiAccessToken();
  if (!token) {
    throw new Error("Missing auth token");
  }

  const form = new FormData();
  form.append("frame", input.blob, `frame-${input.frameSeq}.jpg`);
  form.append("session_id", input.sessionId);
  form.append("client_ts_ms", String(input.clientTsMs));
  form.append("frame_seq", String(input.frameSeq));

  const path = "/api/v1/monitoring/detect";
  const res = await fetch(`${getApiBaseForPath(path)}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Detect request failed: ${res.status}`);
  }
  return (await res.json()) as DetectResponse;
}
