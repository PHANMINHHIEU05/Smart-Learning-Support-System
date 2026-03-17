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
    apiFetch<UserSetting>("/api/v1/settings")
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
          monitoring_mode: s.monitoring_mode ?? "external_camera",
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
      const updated = await apiFetch<UserSetting>("/api/v1/settings", {
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
      <div>
        <h1 className="text-2xl font-bold mb-6">Settings</h1>
        <p className="text-gray-400 text-sm">Loading…</p>
      </div>
    );
  }

  if (!settings) return null;

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 mb-4 text-sm">
          {error}
        </div>
      )}
      {saved && (
        <div className="bg-green-50 border border-green-200 text-green-700 rounded p-3 mb-4 text-sm">
          Settings saved ✓
        </div>
      )}

      <form
        onSubmit={handleSave}
        className="bg-white rounded-xl shadow p-6 space-y-5"
      >
        {/* General */}
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            General
          </h2>
          <div className="space-y-3">
            <label className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                Timezone
              </span>
              <input
                type="text"
                value={form.timezone ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, timezone: e.target.value }))
                }
                className="w-40 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                Daily goal (minutes)
              </span>
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
                className="w-24 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
          </div>
        </section>

        <hr />

        {/* Pomodoro */}
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Pomodoro
          </h2>
          <div className="space-y-3">
            {[
              {
                label: "Focus (minutes)",
                key: "pomodoro_focus_minutes" as const,
                min: 1,
                max: 120,
              },
              {
                label: "Short break (minutes)",
                key: "pomodoro_break_minutes" as const,
                min: 1,
                max: 60,
              },
              {
                label: "Long break (minutes)",
                key: "pomodoro_long_break_minutes" as const,
                min: 1,
                max: 120,
              },
              {
                label: "Cycles before long break",
                key: "pomodoro_cycles_before_long_break" as const,
                min: 1,
                max: 10,
              },
            ].map(({ label, key, min, max }) => (
              <label key={key} className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  {label}
                </span>
                <input
                  type="number"
                  min={min}
                  max={max}
                  value={form[key] ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, [key]: Number(e.target.value) }))
                  }
                  className="w-24 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </label>
            ))}
          </div>
        </section>

        <hr />

        {/* AI Monitoring */}
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            AI Monitoring
          </h2>
          <div className="space-y-3">
            <label className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
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
                className="w-4 h-4 text-blue-600 rounded"
              />
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                Default monitoring mode
              </span>
              <select
                value={form.monitoring_mode ?? "external_camera"}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    monitoring_mode: e.target.value,
                  }))
                }
                className="w-40 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="external_camera">External camera</option>
                <option value="in_web_widget">In-web widget</option>
                <option value="alerts_only">Alerts only</option>
              </select>
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
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
                className="w-4 h-4 text-blue-600 rounded"
              />
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                Data retention (days)
              </span>
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
                className="w-24 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
          </div>
        </section>

        <div className="pt-2">
          <button
            type="submit"
            disabled={saving}
            className="w-full bg-blue-600 text-white rounded-lg py-2.5 font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving…" : "Save Settings"}
          </button>
        </div>
      </form>
    </div>
  );
}
