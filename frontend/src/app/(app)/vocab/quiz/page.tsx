"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { VocabEntry } from "@/types/api";

type QuizMode = "meaning-choice" | "cloze-typing";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function normalizeAnswer(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

function shuffle<T>(items: T[]): T[] {
  return [...items].sort(() => Math.random() - 0.5);
}

function meaningOf(entry: VocabEntry): string {
  return entry.translation_vi || entry.meaning || "No Vietnamese meaning saved.";
}

function clozeSentence(entry: VocabEntry): string {
  if (!entry.example_sentence) {
    return "No context sentence saved for this word yet.";
  }
  const pattern = new RegExp(escapeRegExp(entry.term), "gi");
  return entry.example_sentence.replace(pattern, "_____");
}

export default function VocabQuizPage() {
  const [cards, setCards] = useState<VocabEntry[]>([]);
  const [index, setIndex] = useState(0);
  const [mode, setMode] = useState<QuizMode>("meaning-choice");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [typedAnswer, setTypedAnswer] = useState("");
  const [result, setResult] = useState<"correct" | "wrong" | null>(null);

  const current = cards[index];
  const finished = !loading && cards.length > 0 && index >= cards.length;

  const choiceOptions = useMemo(() => {
    if (!current) return [];
    const distractors = shuffle(
      cards.filter((entry) => entry.vocab_id !== current.vocab_id),
    ).slice(0, 3);
    return shuffle([current, ...distractors]);
  }, [cards, current]);

  useEffect(() => {
    apiFetch<VocabEntry[]>("/api/v1/vocab/due?limit=30")
      .then((result) => setCards(shuffle(result ?? [])))
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load quiz words"),
      )
      .finally(() => setLoading(false));
  }, []);

  const submitResult = async (correct: boolean) => {
    if (!current) return;
    setSaving(true);
    setError(null);
    try {
      await apiFetch<VocabEntry>(
        `/api/v1/vocab/${current.vocab_id}/quiz-result`,
        {
          method: "POST",
          body: JSON.stringify({
            correct,
            reviewed_at: new Date().toISOString(),
          }),
        },
      );
      setResult(correct ? "correct" : "wrong");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save quiz result");
    } finally {
      setSaving(false);
    }
  };

  const selectChoice = async (entry: VocabEntry) => {
    if (saving || result) return;
    setSelectedId(entry.vocab_id);
    await submitResult(entry.vocab_id === current?.vocab_id);
  };

  const submitTypedAnswer = async (event: FormEvent) => {
    event.preventDefault();
    if (!current || saving || result) return;
    await submitResult(normalizeAnswer(typedAnswer) === normalizeAnswer(current.term));
  };

  const moveNext = () => {
    setIndex((value) => value + 1);
    setSelectedId(null);
    setTypedAnswer("");
    setResult(null);
  };

  const switchMode = (nextMode: QuizMode) => {
    setMode(nextMode);
    setSelectedId(null);
    setTypedAnswer("");
    setResult(null);
  };

  return (
    <div className="app-page fg-shell">
      <div className="page-header fg-header-card">
        <div>
          <h1 className="page-title fg-title-glow">Vocabulary Quiz</h1>
          <p className="page-subtitle fg-muted-text">
            Answer due words actively. Correct answers move the word forward;
            wrong answers reset it to box 1.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/vocab/flashcards" className="btn-primary">
            Flashcards
          </Link>
          <Link href="/vocab" className="fg-link-inline">
            Back to library
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-400/40 bg-rose-500/15 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      <section className="mx-auto w-full max-w-4xl">
        {loading ? (
          <div className="fg-card p-8 text-center">
            <p className="fg-subtle">Loading quiz...</p>
          </div>
        ) : cards.length === 0 ? (
          <div className="fg-card p-8 text-center">
            <h2 className="text-2xl font-semibold fg-title-glow">
              No due quiz words
            </h2>
            <p className="mt-2 fg-muted-text">
              Add words from the Firefox extension or wait until scheduled words
              become due.
            </p>
          </div>
        ) : finished ? (
          <div className="fg-card p-8 text-center">
            <h2 className="text-2xl font-semibold fg-title-glow">
              Quiz complete
            </h2>
            <p className="mt-2 fg-muted-text">
              You answered {cards.length} due words.
            </p>
            <Link href="/vocab" className="btn-primary mt-5 inline-flex">
              Return to Vocabulary
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm text-slate-400">
                Word {index + 1} of {cards.length} · Box {current.study_box}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => switchMode("meaning-choice")}
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.08em] ${
                    mode === "meaning-choice"
                      ? "border-cyan-300 bg-cyan-400/25 text-cyan-100"
                      : "border-indigo-400/40 bg-slate-900/30 text-slate-300"
                  }`}
                >
                  Meaning choice
                </button>
                <button
                  type="button"
                  onClick={() => switchMode("cloze-typing")}
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.08em] ${
                    mode === "cloze-typing"
                      ? "border-cyan-300 bg-cyan-400/25 text-cyan-100"
                      : "border-indigo-400/40 bg-slate-900/30 text-slate-300"
                  }`}
                >
                  Fill blank
                </button>
              </div>
            </div>

            <article className="fg-card min-h-[460px] p-6 md:p-9">
              {mode === "meaning-choice" ? (
                <div className="space-y-6">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                      Choose the English word
                    </p>
                    <h2 className="mt-3 text-2xl font-semibold text-slate-100">
                      {meaningOf(current)}
                    </h2>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    {choiceOptions.map((entry) => {
                      const isSelected = selectedId === entry.vocab_id;
                      const isCorrect = entry.vocab_id === current.vocab_id;
                      const showFeedback = Boolean(result);
                      return (
                        <button
                          key={entry.vocab_id}
                          type="button"
                          disabled={saving || Boolean(result)}
                          onClick={() => selectChoice(entry)}
                          className={`min-h-20 rounded-lg border px-4 py-3 text-left text-lg font-semibold ${
                            showFeedback && isCorrect
                              ? "border-emerald-300 bg-emerald-400/20 text-emerald-100"
                              : showFeedback && isSelected
                                ? "border-rose-300 bg-rose-400/20 text-rose-100"
                                : "border-indigo-400/40 bg-slate-900/45 text-slate-100 hover:border-cyan-300"
                          }`}
                        >
                          {entry.term}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <form onSubmit={submitTypedAnswer} className="space-y-6">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                      Type the missing English word
                    </p>
                    <p className="mt-3 rounded-lg bg-slate-900/45 px-4 py-4 text-lg leading-8 text-slate-100">
                      {clozeSentence(current)}
                    </p>
                    <p className="mt-3 text-sm font-semibold text-cyan-100">
                      {meaningOf(current)}
                    </p>
                  </div>

                  <div>
                    <label className="field-label">Answer</label>
                    <input
                      value={typedAnswer}
                      onChange={(event) => setTypedAnswer(event.target.value)}
                      className="field-input"
                      disabled={saving || Boolean(result)}
                      autoFocus
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={saving || Boolean(result) || !typedAnswer.trim()}
                    className="btn-primary"
                  >
                    Submit
                  </button>
                </form>
              )}

              {result && (
                <div
                  className={`mt-6 rounded-lg border px-4 py-3 ${
                    result === "correct"
                      ? "border-emerald-300/50 bg-emerald-400/15 text-emerald-100"
                      : "border-rose-300/50 bg-rose-400/15 text-rose-100"
                  }`}
                >
                  <p className="font-semibold">
                    {result === "correct" ? "Correct" : "Wrong"}:{" "}
                    {current.term}
                  </p>
                  {current.collocation && (
                    <p className="mt-2 text-sm">{current.collocation}</p>
                  )}
                  {current.example_sentence && (
                    <p className="mt-2 text-sm text-slate-200">
                      {current.example_sentence}
                    </p>
                  )}
                </div>
              )}
            </article>

            <div className="flex justify-end">
              <button
                type="button"
                disabled={!result}
                onClick={moveNext}
                className="btn-primary disabled:opacity-45"
              >
                Next Word
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
