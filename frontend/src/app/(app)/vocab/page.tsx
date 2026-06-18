"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch, getApiAccessToken, SPRING_API_BASE } from "@/lib/api-client";
import type { ReviewQuality, VocabEntry, VocabStatus } from "@/types/api";

const STATUS_TABS: VocabStatus[] = [
  "not_started",
  "learning",
  "fuzzy",
  "remembered",
  "mastered",
  "archived",
];

const REVIEW_ACTIONS: Array<{ quality: ReviewQuality; label: string }> = [
  { quality: "hard", label: "Hard" },
  { quality: "fuzzy", label: "Fuzzy" },
  { quality: "remembered", label: "Remembered" },
  { quality: "easy", label: "Easy" },
];

function formatDateTime(value: string | null): string {
  if (!value) return "Never";
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusLabel(value: VocabStatus): string {
  return value.replace("_", " ");
}

export default function VocabPage() {
  const [activeStatus, setActiveStatus] = useState<VocabStatus>("not_started");
  const [entries, setEntries] = useState<VocabEntry[]>([]);
  const [dueEntries, setDueEntries] = useState<VocabEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [manualTerm, setManualTerm] = useState("");
  const [manualMeaning, setManualMeaning] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [tokenStatus, setTokenStatus] = useState<string | null>(null);

  const dueCount = dueEntries.length;
  const reviewLoad = useMemo(
    () => entries.filter((entry) => entry.status !== "archived").length,
    [entries],
  );

  const fetchEntries = (status: VocabStatus) => {
    setLoading(true);
    setError(null);
    Promise.all([
      apiFetch<VocabEntry[]>(`/api/v1/vocab/?status=${status}&limit=100`),
      apiFetch<VocabEntry[]>("/api/v1/vocab/due?limit=50"),
    ])
      .then(([list, due]) => {
        setEntries(list ?? []);
        setDueEntries(due ?? []);
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load vocabulary"),
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchEntries(activeStatus);
  }, [activeStatus]);

  const handleManualSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!manualTerm.trim()) return;

    setSaving(true);
    setError(null);
    try {
      await apiFetch<VocabEntry>("/api/v1/vocab/capture", {
        method: "POST",
        body: JSON.stringify({
          term: manualTerm.trim(),
          ...(manualMeaning.trim() ? { meaning: manualMeaning.trim() } : {}),
          page_title: "Manual web app entry",
        }),
      });
      setManualTerm("");
      setManualMeaning("");
      fetchEntries(activeStatus);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save vocabulary");
    } finally {
      setSaving(false);
    }
  };

  const handleReview = async (entry: VocabEntry, quality: ReviewQuality) => {
    setError(null);
    try {
      await apiFetch<VocabEntry>(`/api/v1/vocab/${entry.vocab_id}/review`, {
        method: "POST",
        body: JSON.stringify({
          quality,
          reviewed_at: new Date().toISOString(),
        }),
      });
      fetchEntries(activeStatus);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to review word");
    }
  };

  const copyExtensionToken = async () => {
    setTokenStatus(null);
    const token = await getApiAccessToken({ forceRefresh: true });
    if (!token) {
      setTokenStatus("No active login token found.");
      return;
    }

    try {
      await navigator.clipboard.writeText(token);
      setTokenStatus("Token copied. Paste it into the Firefox extension popup.");
    } catch {
      setTokenStatus("Could not copy automatically. Refresh and try again.");
    }
  };

  return (
    <div className="app-page fg-shell">
      <div className="page-header fg-header-card">
        <div>
          <h1 className="page-title fg-title-glow">Vocabulary</h1>
          <p className="page-subtitle fg-muted-text">
            Capture words from Firefox, review due cards, and keep memory state
            visible.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="fg-chip">{dueCount} due</span>
          <span className="fg-chip">{reviewLoad} active</span>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-400/40 bg-rose-500/15 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      <section className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="fg-card p-4">
            <div className="mb-4 flex flex-wrap gap-2">
              {STATUS_TABS.map((status) => (
                <button
                  key={status}
                  onClick={() => setActiveStatus(status)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.08em] ${
                    activeStatus === status
                      ? "border-cyan-300 bg-cyan-400/25 text-cyan-100"
                      : "border-indigo-400/40 bg-slate-900/30 text-slate-300 hover:border-cyan-300"
                  }`}
                >
                  {statusLabel(status)}
                </button>
              ))}
            </div>

            {loading ? (
              <p className="fg-subtle text-sm">Loading vocabulary...</p>
            ) : entries.length === 0 ? (
              <p className="fg-subtle text-sm">
                No words in {statusLabel(activeStatus)}.
              </p>
            ) : (
              <div className="space-y-3">
                {entries.map((entry) => (
                  <article
                    key={entry.vocab_id}
                    className="rounded-xl border border-indigo-400/40 bg-slate-900/35 px-4 py-3"
                  >
                    <div className="flex flex-wrap items-start gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h2 className="text-lg font-semibold text-slate-100">
                            {entry.term}
                          </h2>
                          <span className="rounded-full bg-cyan-400/15 px-2 py-0.5 text-xs font-semibold uppercase text-cyan-100">
                            {statusLabel(entry.status)}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-slate-300">
                          {entry.meaning || "Meaning not added yet."}
                        </p>
                        {entry.example_sentence && (
                          <p className="mt-2 text-xs text-slate-400">
                            {entry.example_sentence}
                          </p>
                        )}
                        <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
                          <span>Next: {formatDateTime(entry.next_review_at)}</span>
                          <span>Interval: {entry.interval_days}d</span>
                          <span>Reps: {entry.repetition_count}</span>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {REVIEW_ACTIONS.map((action) => (
                          <button
                            key={action.quality}
                            onClick={() => handleReview(entry, action.quality)}
                            className="rounded-lg border border-cyan-400/40 bg-cyan-400/15 px-2 py-1 text-xs font-semibold text-cyan-200 hover:bg-cyan-400/25"
                          >
                            {action.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-4">
          <section className="fg-card p-4">
            <h2 className="text-lg font-semibold fg-title-glow">Due Review</h2>
            <div className="mt-3 space-y-2">
              {dueEntries.length === 0 ? (
                <p className="fg-subtle text-sm">No due words right now.</p>
              ) : (
                dueEntries.slice(0, 6).map((entry) => (
                  <div
                    key={entry.vocab_id}
                    className="rounded-lg border border-indigo-400/40 bg-slate-900/35 px-3 py-2"
                  >
                    <p className="text-sm font-semibold text-slate-100">
                      {entry.term}
                    </p>
                    <p className="text-xs text-slate-400">
                      {entry.meaning || "Meaning not added yet."}
                    </p>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="fg-card p-4">
            <h2 className="text-lg font-semibold fg-title-glow">
              Firefox Extension
            </h2>
            <p className="mt-2 text-sm fg-muted-text">
              Spring API: {SPRING_API_BASE}
            </p>
            <button
              onClick={copyExtensionToken}
              className="btn-primary mt-4 w-full"
            >
              Copy Extension Token
            </button>
            {tokenStatus && (
              <p className="mt-3 text-xs text-cyan-100">{tokenStatus}</p>
            )}
          </section>

          <section className="fg-card p-4">
            <h2 className="text-lg font-semibold fg-title-glow">Manual Add</h2>
            <form onSubmit={handleManualSave} className="mt-4 space-y-3">
              <div>
                <label className="field-label">Word</label>
                <input
                  value={manualTerm}
                  onChange={(e) => setManualTerm(e.target.value)}
                  className="field-input"
                  required
                />
              </div>
              <div>
                <label className="field-label">Meaning</label>
                <textarea
                  value={manualMeaning}
                  onChange={(e) => setManualMeaning(e.target.value)}
                  className="field-textarea"
                  rows={3}
                />
              </div>
              <button disabled={saving} className="btn-primary w-full">
                {saving ? "Saving..." : "Save Word"}
              </button>
            </form>
          </section>
        </aside>
      </section>
    </div>
  );
}
