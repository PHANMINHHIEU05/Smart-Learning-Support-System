// TypeScript types matching backend schemas

export type TaskStatus = "todo" | "doing" | "done" | "archived";
export type BlockType = "focus" | "break" | "long_break";
export type SessionMode = "pomodoro" | "free";
export type EndReason = "completed" | "stopped" | "timeout" | "error";

export interface Task {
  task_id: string;
  user_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: number;
  due_at: string | null;
  estimated_minutes: number | null;
  subject_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
  priority?: number;
  due_at?: string;
  estimated_minutes?: number;
  subject_name?: string;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: number;
  due_at?: string;
  estimated_minutes?: number;
  subject_name?: string;
}

export interface StudySession {
  session_id: string;
  user_id: string;
  task_id: string | null;
  planned_mode: SessionMode;
  started_at: string;
  ended_at: string | null;
  end_reason: EndReason | null;
}

export interface SessionCreate {
  task_id?: string;
  planned_mode: SessionMode;
  started_at: string;
}

export interface SessionEnd {
  ended_at: string;
  end_reason: EndReason;
}

export interface SessionBlock {
  block_id: string;
  session_id: string;
  block_type: BlockType;
  started_at: string;
  ended_at: string | null;
  planned_duration_seconds: number;
}

export interface BlockCreate {
  session_id: string;
  block_type: BlockType;
  start_at: string;
  planned_duration_seconds: number;
}

export interface DailySummary {
  date: string;
  total_focus_seconds: number;
  total_break_seconds: number;
  distraction_count: number;
  fatigue_count: number;
  session_count: number;
}

export interface FocusHeatmapCell {
  day_of_week: number;
  slot_index: number;
  slot_label: string;
  avg_focus_score: number;
  event_count: number;
  focused_event_count: number;
  distracted_event_count: number;
}

export interface EnemyStats {
  date_from: string;
  date_to: string;
  phone_detected_count: number;
  book_detected_count: number;
  phone_book_count: number;
  drowsy_slump_count: number;
  session_count: number;
  phone_per_session: number;
  total_events: number;
}

export interface EngagementSummary {
  completed_focus_blocks: number;
  total_points: number; // Legacy field for backward compatibility
  points_earned: number; // NEW: Points gained from focus blocks
  points_deducted: number; // NEW: Points deducted from distractions
  points_net: number; // NEW: Net score (earned - deducted)
  current_level: number;
  next_level_points: number;
  progress_pct: number;
  points_per_focus_block: number;
}

export interface PenaltyEvent {
  event_id?: string | null;
  event_type: string;
  event_time: string;
  points_deducted: number;
}

export interface PenaltyHistoryResponse {
  user_id: string;
  date_from: string;
  date_to: string;
  total_penalties: number;
  events: PenaltyEvent[];
}

export interface WhiteNoisePreset {
  id: string;
  label: string;
  description: string;
}

export interface UserSetting {
  user_id: string;
  timezone: string;
  daily_goal_minutes: number;
  pomodoro_focus_minutes: number;
  pomodoro_break_minutes: number;
  pomodoro_long_break_minutes: number;
  pomodoro_cycles_before_long_break: number;
  ai_monitoring_enabled: boolean;
  retention_days: number;
  monitoring_mode: string | null;
  critical_sound_enabled: boolean | null;
  updated_at: string;
}

export interface UserSettingUpdate {
  timezone?: string;
  daily_goal_minutes?: number;
  pomodoro_focus_minutes?: number;
  pomodoro_break_minutes?: number;
  pomodoro_long_break_minutes?: number;
  pomodoro_cycles_before_long_break?: number;
  ai_monitoring_enabled?: boolean;
  retention_days?: number;
  monitoring_mode?: string;
  critical_sound_enabled?: boolean;
}

// ── Vocabulary ──────────────────────────────────────────────────────────────

export type VocabStatus =
  | "not_started"
  | "learning"
  | "fuzzy"
  | "remembered"
  | "mastered"
  | "archived";

export type ReviewQuality = "hard" | "fuzzy" | "remembered" | "easy";

export interface VocabEntry {
  vocab_id: string;
  user_id: string;
  term: string;
  meaning: string | null;
  translation_vi: string | null;
  definition_en: string | null;
  example_sentence: string | null;
  collocation: string | null;
  part_of_speech: string | null;
  phonetic: string | null;
  audio_url: string | null;
  dictionary_provider: string | null;
  translation_provider: string | null;
  source_type: string | null;
  source_ref: string | null;
  status: VocabStatus;
  ease_factor: number;
  interval_days: number;
  repetition_count: number;
  study_box: number;
  next_review_at: string;
  last_reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VocabCaptureRequest {
  term: string;
  meaning?: string;
  translation_vi?: string;
  definition_en?: string;
  example_sentence?: string;
  collocation?: string;
  part_of_speech?: string;
  phonetic?: string;
  audio_url?: string;
  dictionary_provider?: string;
  translation_provider?: string;
  context_sentence?: string;
  page_url?: string;
  page_title?: string;
}

export interface VocabLookupResponse {
  term: string;
  normalized_term: string;
  meaning: string | null;
  translation_vi: string | null;
  definition_en: string | null;
  example_sentence: string | null;
  collocation?: string | null;
  part_of_speech: string | null;
  phonetic: string | null;
  audio_url: string | null;
  dictionary_provider: string | null;
  translation_provider: string | null;
  source_type: string;
  source_ref: string | null;
  already_saved: boolean;
}

// ── Monitoring ──────────────────────────────────────────────────────────────

export type MonitoringMode = "browser_camera" | "alerts_only";
export type MonitoringProcessStatus =
  | "idle"
  | "starting"
  | "active"
  | "degraded"
  | "stopped";

export interface DegradedReason {
  code: string;
  message: string;
  recoverable: boolean;
  fallback_mode: string;
}

export interface MonitoringStatusResponse {
  status: MonitoringProcessStatus;
  active_mode: string | null;
  pid: number | null;
  degraded_reason: DegradedReason | null;
  severity_defaults: Record<string, string[]>;
}

export interface ModeSwitchResponse {
  requested_mode: string;
  applied_mode: string;
  status: MonitoringProcessStatus;
  degraded_reason: DegradedReason | null;
  persisted: boolean;
}

export type InterventionEscalationLevel = "none" | "warning" | "paused";
export type InterventionPauseReason = "distraction" | "leave_seat";

export interface InterventionStateResponse {
  escalation_level: InterventionEscalationLevel;
  latest_alert: Record<string, unknown> | null;
  pause_reason: InterventionPauseReason | null;
  resume_countdown_sec: number | null;
  last_update_ts: string;
}

export interface CameraTelemetry {
  user_id: string;
  timestamp: string;
  python_fps: number | null;
  web_fps: number | null;
  frame_latency_ms: number | null;
  camera_resolution: string;
  processing_resolution: string;
  notes?: string | null;
}

// ── Alerts ───────────────────────────────────────────────────────────────────

export interface AlertResponse {
  alert_id: string;
  user_id: string;
  session_id: string | null;
  rule_id: string | null;
  event_id: string | null;
  fired_at: string;
  channel: string | null;
  message: string | null;
  payload_json: unknown;
}

// ── AI Events ───────────────────────────────────────────────────────────────

export interface AiEventResponse {
  event_id: string;
  user_id: string;
  session_id: string | null;
  event_type: string;
  start_at: string;
  end_at: string | null;
  confidence: number;
  severity: number | null;
  payload_json: unknown;
}
