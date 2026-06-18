"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/providers/AuthProvider";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "◉" },
  { href: "/tasks", label: "Tasks", icon: "▣" },
  { href: "/vocab", label: "Vocab", icon: "Aa" },
  { href: "/timer", label: "Timer", icon: "◍" },
  { href: "/analytics", label: "Analytics", icon: "◌" },
  { href: "/settings", label: "Settings", icon: "◎" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { session, loading, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !session) {
      router.replace("/login");
    }
  }, [session, loading, router]);

  if (loading) {
    return (
      <div className="fg-shell min-h-screen flex items-center justify-center px-4">
        <div className="fg-card w-full max-w-sm p-6 text-center">
          <p className="text-sm uppercase tracking-[0.18em] fg-subtle">SLSS</p>
          <p className="mt-2 text-lg font-semibold fg-title-glow">
            Loading workspace...
          </p>
        </div>
      </div>
    );
  }

  if (!session) return null;

  return (
    <div className="fg-shell min-h-screen px-3 pb-6 pt-4 md:px-5 md:pt-6">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-4 lg:flex-row lg:gap-6">
        <aside className="fg-card w-full overflow-hidden lg:sticky lg:top-6 lg:w-72 lg:self-start">
          <div className="border-b border-indigo-500/40 p-5">
            <p className="text-xs uppercase tracking-[0.22em] fg-subtle">
              Smart Learning
            </p>
            <div className="mt-2 flex items-center justify-between">
              <span className="text-2xl font-bold fg-title-glow">SLSS</span>
              <span className="fg-chip">Focus Mode</span>
            </div>
          </div>

          <nav className="px-3 pb-3 pt-3">
            <div className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible">
              {NAV_ITEMS.map(({ href, label, icon }) => {
                const active = pathname === href;
                return (
                  <Link
                    key={href}
                    href={href}
                    prefetch
                    onMouseEnter={() => router.prefetch(href)}
                    onFocus={() => router.prefetch(href)}
                    className={`group flex min-w-max items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold lg:min-w-0 ${
                      active
                        ? "bg-cyan-400/25 text-cyan-200"
                        : "text-slate-300 hover:bg-indigo-500/20 hover:text-cyan-100"
                    }`}
                  >
                    <span
                      className={active ? "text-cyan-100" : "text-cyan-300"}
                    >
                      {icon}
                    </span>
                    <span>{label}</span>
                  </Link>
                );
              })}
            </div>
          </nav>

          <div className="border-t border-indigo-500/40 p-4">
            <p className="truncate text-xs fg-subtle">{session.user.email}</p>
            <button onClick={signOut} className="btn-danger mt-3 w-full">
              Sign Out
            </button>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <div className="fg-card min-h-[calc(100vh-3rem)] p-4 md:p-6 lg:p-7">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
