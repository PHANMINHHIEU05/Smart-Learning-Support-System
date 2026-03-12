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
}

export interface SessionEnd {
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
}
