"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { UserSetting, UserSettingUpdate } from "@/types/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSetting | null>(null);
  const [form, setForm] = useState<UserSettingUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch<UserSetting>("/api/v1/settings/")
      .then((s) => {
        setSettings(s);
        setForm({
          timezone: s.timezone,
          daily_goal_minutes: s.daily_goal_minutes,
          pomodoro_focus_minutes: s.pomodoro_focus_minutes,
          pomodoro_break_minutes: s.pomodoro_break_minutes,
          pomodoro_long_break_minutes: s.pomodoro_long_break_minutes,
          pomodoro_cycles_before_long_break:
            s.pomodoro_cycles_before_long_break,
          ai_monitoring_enabled: s.ai_monitoring_enabled,
          retention_days: s.retention_days,
          monitoring_mode:
            s.monitoring_mode === "in_web_widget" ||
            s.monitoring_mode === "external_camera"
              ? "browser_camera"
              : (s.monitoring_mode ?? "browser_camera"),
          critical_sound_enabled: s.critical_sound_enabled ?? true,
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await apiFetch<UserSetting>("/api/v1/settings/", {
        method: "PUT",
        body: JSON.stringify(form),
      });
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="app-page fg-shell">
        <h1 className="page-title fg-title-glow">Settings</h1>
        <p className="text-sm fg-subtle">Loading...</p>
      </div>
    );
  }

  if (!settings) return null;

  return (
    <div className="app-page fg-shell">
      <div className="fg-header-card">
        <h1 className="page-title fg-title-glow">Settings</h1>
        <p className="page-subtitle fg-muted-text">
          Tune timer defaults, monitoring behavior, and retention controls.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}
      {saved && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          Settings saved successfully.
        </div>
      )}

      <form
        onSubmit={handleSave}
        className="fg-card p-5 md:p-7 space-y-7 max-w-3xl"
      >
        <section>
          <h2 className="text-lg font-bold text-slate-100">General</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <label className="field-label">Timezone</label>
              <input
                type="text"
                value={form.timezone ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, timezone: e.target.value }))
                }
                className="field-input"
              />
            </div>
            <div>
              <label className="field-label">Daily Goal (Minutes)</label>
              <input
                type="number"
                min={1}
                max={1440}
                value={form.daily_goal_minutes ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    daily_goal_minutes: Number(e.target.value),
                  }))
                }
                className="field-input"
              />
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-bold text-slate-100">Pomodoro</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {[
              {
                label: "Focus (minutes)",
                key: "pomodoro_focus_minutes" as const,
                min: 1,
                max: 120,
              },
              {
                label: "Short Break (minutes)",
                key: "pomodoro_break_minutes" as const,
                min: 1,
                max: 60,
              },
              {
                label: "Long Break (minutes)",
                key: "pomodoro_long_break_minutes" as const,
                min: 1,
                max: 120,
              },
              {
                label: "Cycles Before Long Break",
                key: "pomodoro_cycles_before_long_break" as const,
                min: 1,
                max: 10,
              },
            ].map(({ label, key, min, max }) => (
              <div key={key}>
                <label className="field-label">{label}</label>
                <input
                  type="number"
                  min={min}
                  max={max}
                  value={form[key] ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, [key]: Number(e.target.value) }))
                  }
                  className="field-input"
                />
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-lg font-bold text-slate-100">AI Monitoring</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="rounded-xl border border-indigo-400/40 bg-slate-900/35 px-4 py-3 flex items-center justify-between">
              <span className="text-sm font-medium text-slate-200">
                Enable AI monitoring
              </span>
              <input
                type="checkbox"
                checked={form.ai_monitoring_enabled ?? true}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    ai_monitoring_enabled: e.target.checked,
                  }))
                }
                className="h-4 w-4 rounded border-slate-300 text-cyan-600"
              />
            </label>
            <div>
              <label className="field-label">Default Monitoring Mode</label>
              <select
                value={form.monitoring_mode ?? "browser_camera"}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    monitoring_mode: e.target.value,
                  }))
                }
                className="field-select"
              >
                <option value="browser_camera">Browser camera</option>
                <option value="alerts_only">Alerts only</option>
              </select>
            </div>
            <label className="rounded-xl border border-indigo-400/40 bg-slate-900/35 px-4 py-3 flex items-center justify-between">
              <span className="text-sm font-medium text-slate-200">
                Critical alert sound
              </span>
              <input
                type="checkbox"
                checked={form.critical_sound_enabled ?? true}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    critical_sound_enabled: e.target.checked,
                  }))
                }
                className="h-4 w-4 rounded border-slate-300 text-cyan-600"
              />
            </label>
            <div>
              <label className="field-label">Data Retention (days)</label>
              <input
                type="number"
                min={1}
                max={90}
                value={form.retention_days ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    retention_days: Number(e.target.value),
                  }))
                }
                className="field-input"
              />
            </div>
          </div>
        </section>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="btn-primary disabled:opacity-60"
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </form>
    </div>
  );
}
