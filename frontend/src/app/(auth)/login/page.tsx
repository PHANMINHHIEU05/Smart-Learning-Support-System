"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createSupabaseClient } from "@/lib/supabase";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const supabase = createSupabaseClient();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      router.push("/dashboard");
    }
  };

  return (
    <div className="min-h-screen grid place-items-center px-4 py-8">
      <div className="surface-card surface-card-strong stagger-item w-full max-w-5xl overflow-hidden">
        <div className="grid md:grid-cols-[1.15fr_1fr]">
          <section className="hidden bg-gradient-to-br from-cyan-700 via-sky-700 to-orange-500 p-8 text-white md:block md:p-10">
            <p className="text-xs uppercase tracking-[0.24em] text-cyan-100">
              Smart Learning Support
            </p>
            <h1 className="mt-4 text-4xl font-bold leading-tight">
              Build Deep Focus Sessions Without Burnout
            </h1>
            <p className="mt-4 text-sm text-cyan-50/90">
              AI-assisted monitoring, adaptive interventions, and clean analytics
              in one focused workspace.
            </p>
            <div className="mt-8 space-y-3 text-sm text-cyan-50/95">
              <p className="rounded-xl border border-white/25 bg-white/15 px-3 py-2">
                Live camera stream with low-latency metrics
              </p>
              <p className="rounded-xl border border-white/25 bg-white/15 px-3 py-2">
                Pomodoro cycle + ergonomic nudges
              </p>
              <p className="rounded-xl border border-white/25 bg-white/15 px-3 py-2">
                Earned vs deducted engagement visibility
              </p>
            </div>
          </section>

          <section className="p-6 md:p-10">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Welcome back</p>
            <h2 className="mt-2 text-3xl font-bold text-slate-900">Sign In</h2>
            <p className="mt-1 text-sm text-slate-500">
              Continue your study flow from where you left off.
            </p>

            <form onSubmit={handleLogin} className="mt-7 space-y-4">
              <div>
                <label className="field-label" htmlFor="email">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="field-input"
                />
              </div>
              <div>
                <label className="field-label" htmlFor="password">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="field-input"
                />
              </div>

              {error && (
                <p
                  className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
                  role="alert"
                >
                  {error}
                </p>
              )}

              <button type="submit" disabled={loading} className="btn-primary w-full disabled:opacity-60">
                {loading ? "Signing in..." : "Sign In"}
              </button>
            </form>

            <p className="mt-5 text-sm text-slate-600">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="font-semibold text-cyan-700 hover:text-cyan-800">
                Register
              </Link>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
