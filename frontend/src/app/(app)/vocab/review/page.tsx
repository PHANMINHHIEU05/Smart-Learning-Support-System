"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { ReviewQuality, VocabEntry } from "@/types/api";

const REVIEW_ACTIONS: Array<{
  quality: ReviewQuality;
  label: string;
  hint: string;
}> = [
  { quality: "hard", label: "Hard", hint: "Forgot or guessed" },
  { quality: "fuzzy", label: "Fuzzy", hint: "Partly remembered" },
  { quality: "remembered", label: "Remembered", hint: "Correct with effort" },
  { quality: "easy", label: "Easy", hint: "Immediate recall" },
];

export default function VocabularyReviewPage() {
  const [cards, setCards] = useState<VocabEntry[]>([]);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const current = cards[index];
  const finished = !loading && cards.length > 0 && index >= cards.length;

  useEffect(() => {
    apiFetch<VocabEntry[]>("/api/v1/vocab/due?limit=100")
      .then((result) => setCards(result ?? []))
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load review cards"),
      )
      .finally(() => setLoading(false));
  }, []);

  const playAudio = () => {
    if (!current?.audio_url) return;
    const audio = new Audio(current.audio_url);
    void audio.play().catch(() => window.open(current.audio_url!, "_blank"));
  };

  const submitReview = async (quality: ReviewQuality) => {
    if (!current) return;
    setReviewing(true);
    setError(null);
    try {
      await apiFetch<VocabEntry>(`/api/v1/vocab/${current.vocab_id}/review`, {
        method: "POST",
        body: JSON.stringify({
          quality,
          reviewed_at: new Date().toISOString(),
        }),
      });
      setIndex((value) => value + 1);
      setRevealed(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save review");
    } finally {
      setReviewing(false);
    }
  };

  return (
    <div className="app-page fg-shell">
      <div className="page-header fg-header-card">
        <div>
          <h1 className="page-title fg-title-glow">Vocabulary Review</h1>
          <p className="page-subtitle fg-muted-text">
            Recall first, reveal second, then grade honestly.
          </p>
        </div>
        <Link href="/vocab" className="fg-link-inline">
          Back to library
        </Link>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-400/40 bg-rose-500/15 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      <section className="mx-auto w-full max-w-3xl">
        {loading ? (
          <div className="fg-card p-8 text-center">
            <p className="fg-subtle">Loading due words...</p>
          </div>
        ) : cards.length === 0 ? (
          <div className="fg-card p-8 text-center">
            <h2 className="text-2xl font-semibold fg-title-glow">
              Nothing due right now
            </h2>
            <p className="mt-2 fg-muted-text">
              New review cards will appear when their SRS schedule is due.
            </p>
          </div>
        ) : finished ? (
          <div className="fg-card p-8 text-center">
            <h2 className="text-2xl font-semibold fg-title-glow">
              Review complete
            </h2>
            <p className="mt-2 fg-muted-text">
              You reviewed {cards.length} words in this session.
            </p>
            <Link href="/vocab" className="btn-primary mt-5 inline-flex">
              Return to Vocabulary
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm text-slate-400">
              <span>
                Card {index + 1} of {cards.length}
              </span>
              <span>{cards.length - index - 1} remaining</span>
            </div>

            <article
              className="fg-card min-h-[420px] p-6 md:p-9"
              data-testid="vocab-review-card"
            >
              <div className="flex min-h-[340px] flex-col">
                <div className="text-center">
                  {current.part_of_speech && (
                    <span className="fg-chip">{current.part_of_speech}</span>
                  )}
                  <h2 className="mt-5 text-4xl font-bold text-slate-100">
                    {current.term}
                  </h2>
                  {current.phonetic && (
                    <p className="mt-2 text-sm text-cyan-200">
                      {current.phonetic}
                    </p>
                  )}
                  {current.audio_url && (
                    <button
                      type="button"
                      onClick={playAudio}
                      className="mt-4 rounded-lg border border-cyan-400/40 bg-cyan-400/15 px-3 py-2 text-sm font-semibold text-cyan-100"
                      data-testid="vocab-review-pronounce-button"
                    >
                      Pronounce
                    </button>
                  )}
                </div>

                <div className="mt-8 flex flex-1 flex-col justify-center">
                  {!revealed ? (
                    <button
                      type="button"
                      onClick={() => setRevealed(true)}
                      className="btn-primary mx-auto min-w-44"
                      data-testid="vocab-review-reveal-button"
                    >
                      Reveal Answer
                    </button>
                  ) : (
                    <div className="space-y-4">
                      <div className="border-l-2 border-cyan-300 pl-4">
                        <p className="text-xl font-semibold text-cyan-100">
                          {current.translation_vi ||
                            current.meaning ||
                            "No Vietnamese meaning saved."}
                        </p>
                        {current.definition_en && (
                          <p className="mt-2 text-sm text-slate-300">
                            {current.definition_en}
                          </p>
                        )}
                      </div>
                      {current.example_sentence && (
                        <p className="rounded-lg bg-slate-900/45 px-4 py-3 text-sm text-slate-300">
                          {current.example_sentence}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </article>

            {revealed && (
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {REVIEW_ACTIONS.map((action) => (
                  <button
                    key={action.quality}
                    type="button"
                    disabled={reviewing}
                    onClick={() => submitReview(action.quality)}
                    className="rounded-lg border border-indigo-400/40 bg-slate-900/45 px-3 py-3 text-left hover:border-cyan-300"
                    data-testid={`vocab-review-${action.quality}-button`}
                  >
                    <span className="block text-sm font-semibold text-cyan-100">
                      {action.label}
                    </span>
                    <span className="mt-1 block text-xs text-slate-400">
                      {action.hint}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
