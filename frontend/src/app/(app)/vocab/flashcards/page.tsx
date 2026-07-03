"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { VocabEntry } from "@/types/api";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function HighlightedSentence({
  sentence,
  term,
}: {
  sentence: string;
  term: string;
}) {
  const parts = sentence.split(new RegExp(`(${escapeRegExp(term)})`, "gi"));
  return (
    <>
      {parts.map((part, index) =>
        part.toLowerCase() === term.toLowerCase() ? (
          <strong key={`${part}-${index}`} className="text-cyan-100">
            {part}
          </strong>
        ) : (
          <span key={`${part}-${index}`}>{part}</span>
        ),
      )}
    </>
  );
}

export default function VocabFlashcardsPage() {
  const [cards, setCards] = useState<VocabEntry[]>([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const current = cards[index];

  useEffect(() => {
    apiFetch<VocabEntry[]>("/api/v1/vocab/due?limit=30")
      .then((result) => setCards(result ?? []))
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load flashcards"),
      )
      .finally(() => setLoading(false));
  }, []);

  const playAudio = () => {
    if (!current) return;
    if (current.audio_url) {
      const audio = new Audio(current.audio_url);
      void audio.play().catch(() => window.open(current.audio_url!, "_blank"));
      return;
    }

    if ("SpeechSynthesisUtterance" in window && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(current.term);
      utterance.lang = "en-US";
      utterance.rate = 0.85;
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="app-page fg-shell">
      <div className="page-header fg-header-card">
        <div>
          <h1 className="page-title fg-title-glow">Flashcards</h1>
          <p className="page-subtitle fg-muted-text">
            Scan today&apos;s due words with pronunciation, collocation, and
            TOEIC context.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/vocab/quiz" className="btn-primary">
            Start Quiz
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
            <p className="fg-subtle">Loading flashcards...</p>
          </div>
        ) : cards.length === 0 ? (
          <div className="fg-card p-8 text-center">
            <h2 className="text-2xl font-semibold fg-title-glow">
              Nothing due today
            </h2>
            <p className="mt-2 fg-muted-text">
              Saved learning words will appear here when their review date
              arrives.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm text-slate-400">
              <span>
                Card {index + 1} of {cards.length}
              </span>
              <span>Box {current.study_box}</span>
            </div>

            <article className="fg-card min-h-[480px] p-6 md:p-9">
              <div className="flex min-h-[400px] flex-col justify-between">
                <div className="text-center">
                  {current.part_of_speech && (
                    <span className="fg-chip">{current.part_of_speech}</span>
                  )}
                  <h2 className="mt-5 break-words text-5xl font-bold text-slate-100">
                    {current.term}
                  </h2>
                  {current.phonetic && (
                    <p className="mt-3 text-base text-cyan-200">
                      {current.phonetic}
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={playAudio}
                    className="btn-primary mt-5"
                  >
                    Listen
                  </button>
                </div>

                <div className="mt-8 space-y-4">
                  <div className="rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-cyan-200">
                      Meaning
                    </p>
                    <p className="mt-2 text-lg font-semibold text-slate-100">
                      {current.translation_vi ||
                        current.meaning ||
                        "No Vietnamese meaning saved."}
                    </p>
                  </div>

                  {current.collocation && (
                    <div className="rounded-lg bg-slate-900/40 px-4 py-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                        Collocation
                      </p>
                      <p className="mt-2 text-base font-semibold text-cyan-100">
                        {current.collocation}
                      </p>
                    </div>
                  )}

                  {current.example_sentence && (
                    <div className="rounded-lg bg-slate-900/40 px-4 py-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                        Context
                      </p>
                      <p className="mt-2 text-sm leading-6 text-slate-300">
                        <HighlightedSentence
                          sentence={current.example_sentence}
                          term={current.term}
                        />
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </article>

            <div className="flex flex-wrap justify-between gap-2">
              <button
                type="button"
                disabled={index === 0}
                onClick={() => setIndex((value) => Math.max(0, value - 1))}
                className="rounded-lg border border-indigo-400/40 bg-slate-900/45 px-4 py-2 text-sm font-semibold text-slate-200 disabled:opacity-45"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={index >= cards.length - 1}
                onClick={() =>
                  setIndex((value) => Math.min(cards.length - 1, value + 1))
                }
                className="btn-primary"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
