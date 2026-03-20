"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createSupabaseClient } from "@/lib/supabase";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const supabase = createSupabaseClient();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    const { error } = await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      setSuccess(true);
      setTimeout(() => router.push("/login"), 3000);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen grid place-items-center px-4 py-8">
        <div className="surface-card surface-card-strong stagger-item w-full max-w-lg p-8 text-center">
          <p className="text-xs uppercase tracking-[0.2em] text-emerald-700">Account Created</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900">Check your inbox</h1>
          <p className="mt-2 text-sm text-slate-600">
            We sent a confirmation link to your email. After confirming, you can{" "}
            <Link href="/login" className="font-semibold text-cyan-700 hover:text-cyan-800">
              sign in here
            </Link>
            .
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen grid place-items-center px-4 py-8">
      <div className="surface-card surface-card-strong stagger-item w-full max-w-2xl overflow-hidden p-6 md:p-10">
        <div className="mb-7">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Join SLSS</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900">Create Account</h1>
          <p className="mt-1 text-sm text-slate-500">
            Start with smart monitoring, cleaner focus sessions, and richer analytics.
          </p>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
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
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="field-input"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="confirm">
                Confirm Password
              </label>
              <input
                id="confirm"
                type="password"
                required
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="field-input"
              />
            </div>
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
            {loading ? "Creating account..." : "Register"}
          </button>
        </form>

        <p className="mt-5 text-sm text-slate-600">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-cyan-700 hover:text-cyan-800">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
