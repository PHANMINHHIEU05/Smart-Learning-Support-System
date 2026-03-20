'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/providers/AuthProvider'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: '◉' },
  { href: '/tasks', label: 'Tasks', icon: '▣' },
  { href: '/timer', label: 'Timer', icon: '◍' },
  { href: '/analytics', label: 'Analytics', icon: '◌' },
  { href: '/settings', label: 'Settings', icon: '◎' },
]

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { session, loading, signOut } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!loading && !session) {
      router.replace('/login')
    }
  }, [session, loading, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="surface-card surface-card-strong w-full max-w-sm p-6 text-center">
          <p className="text-sm uppercase tracking-[0.18em] text-slate-500">SLSS</p>
          <p className="mt-2 text-lg font-semibold text-slate-800">Loading workspace...</p>
        </div>
      </div>
    )
  }

  if (!session) return null

  return (
    <div className="min-h-screen px-3 pb-6 pt-4 md:px-5 md:pt-6">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-4 lg:flex-row lg:gap-6">
        <aside className="surface-card surface-card-strong w-full overflow-hidden lg:sticky lg:top-6 lg:w-72 lg:self-start">
          <div className="border-b border-slate-200/70 bg-gradient-to-r from-cyan-50 via-sky-50 to-amber-50 p-5">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
              Smart Learning
            </p>
            <div className="mt-2 flex items-center justify-between">
              <span className="text-2xl font-bold text-slate-900">SLSS</span>
              <span className="ui-pill">Focus Mode</span>
            </div>
          </div>

          <nav className="px-3 pb-3 pt-3">
            <div className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible">
              {NAV_ITEMS.map(({ href, label, icon }) => {
                const active = pathname === href
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`group flex min-w-max items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold lg:min-w-0 ${
                      active
                        ? 'bg-gradient-to-r from-cyan-500 to-sky-600 text-white shadow-lg shadow-cyan-600/30'
                        : 'text-slate-600 hover:bg-white/85 hover:text-slate-900'
                    }`}
                  >
                    <span className={active ? 'text-white' : 'text-cyan-600'}>{icon}</span>
                    <span>{label}</span>
                  </Link>
                )
              })}
            </div>
          </nav>

          <div className="border-t border-slate-200/70 bg-white/50 p-4">
            <p className="truncate text-xs text-slate-500">{session.user.email}</p>
            <button onClick={signOut} className="btn-danger mt-3 w-full">
              Sign Out
            </button>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <div className="surface-card surface-card-muted min-h-[calc(100vh-3rem)] p-4 md:p-6 lg:p-7">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
