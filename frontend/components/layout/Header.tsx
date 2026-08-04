'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { useSession, signOut } from 'next-auth/react'
import Avatar from '@/components/ui/Avatar'
import ThemeToggle from '@/components/ui/ThemeToggle'
import { CloseIcon, MenuIcon } from '@/components/ui/icons'
import { useUnreadNotifications } from '@/features/social/hooks/useUnreadNotifications'
import { profileService } from '@/features/profile/services/profileService'

const APP_NAV = [
  { href: '/dashboard', label: '내 글' },
  { href: '/notifications', label: '알림' },
  { href: '/settings', label: '설정' },
]

export default function Header() {
  const { data: session, status } = useSession()
  const pathname = usePathname()
  const [menuOpen, setMenuOpen] = useState(false)
  const [handle, setHandle] = useState<string | null>(null)
  const toggleRef = useRef<HTMLButtonElement>(null)

  useEffect(() => setMenuOpen(false), [pathname])

  useEffect(() => {
    if (!menuOpen) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false)
        toggleRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [menuOpen])

  // 읽지 않은 알림 수는 서버가 밀어준다 (SSE, 실패 시 폴링으로 대체).
  const unread = useUnreadNotifications(status === 'authenticated')

  // 내 블로그 주소는 헤더에서 늘 보여야 한다.
  useEffect(() => {
    if (status !== 'authenticated') return
    profileService
      .me()
      .then((me) => setHandle(me.handle))
      .catch(() => undefined)
  }, [status, pathname])

  return (
    <header className="fixed inset-x-0 top-0 z-50 bg-bg/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-shell items-center justify-between gap-4 px-4 md:px-6">
        <Link
          href="/"
          className="flex items-center gap-2 text-xl font-bold tracking-tight text-ink"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 2L15 8L22 9L17 14L18 21L12 18L6 21L7 14L2 9L9 8L12 2Z"
              fill="currentColor"
            />
          </svg>
          devshiplog
        </Link>

        <div className="flex items-center gap-1">
          <Link
            href="/search"
            aria-label="검색"
            className="grid h-touch w-touch place-items-center rounded-full text-ink transition-colors hover:bg-surface-2"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
          </Link>

          <ThemeToggle />

          {status === 'authenticated' ? (
            <>
              <Link
                href="/notifications"
                aria-label={unread > 0 ? `알림 ${unread}건` : '알림'}
                className="relative grid h-touch w-touch place-items-center rounded-full text-ink transition-colors hover:bg-surface-2"
              >
                <svg
                  className="h-5 w-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.75}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 8-3 8h18s-3-1-3-8" />
                  <path d="M13.7 21a2 2 0 0 1-3.4 0" />
                </svg>
                {unread > 0 && (
                  <span className="absolute right-2 top-2 grid h-4 min-w-4 place-items-center rounded-full bg-danger px-1 text-[10px] font-bold leading-none text-white">
                    {unread > 99 ? '99+' : unread}
                  </span>
                )}
              </Link>

              <Link
                href="/drafts/new"
                className="ml-1 hidden h-9 items-center rounded border border-ink px-4 text-sm font-bold text-ink transition-colors hover:bg-ink hover:text-bg sm:inline-flex"
              >
                새 글 작성
              </Link>

              <button
                ref={toggleRef}
                type="button"
                onClick={() => setMenuOpen((open) => !open)}
                aria-expanded={menuOpen}
                aria-controls="user-menu"
                aria-label="내 메뉴"
                className="ml-1 grid h-touch w-touch place-items-center rounded-full"
              >
                <Avatar
                  handle={handle ?? session?.user?.email ?? 'me'}
                  displayName={session?.user?.name}
                  size={32}
                />
              </button>
            </>
          ) : (
            <Link
              href="/auth/login"
              className="ml-1 inline-flex h-9 items-center rounded bg-ink px-4 text-sm font-bold text-bg transition-opacity hover:opacity-85"
            >
              로그인
            </Link>
          )}
        </div>
      </div>

      {/* 사용자 메뉴 — 모바일에서는 내비게이션 역할까지 겸한다. */}
      <nav
        id="user-menu"
        aria-label="내 메뉴"
        hidden={!menuOpen}
        className="mx-auto max-w-shell px-4 pb-3 md:px-6"
      >
        <ul className="ml-auto w-full overflow-hidden rounded border border-border bg-surface shadow-pop sm:w-56">
          {handle && (
            <li>
              <Link
                href={`/@${handle}`}
                className="flex min-h-touch items-center px-4 text-sm font-medium text-ink hover:bg-surface-2"
              >
                내 블로그
              </Link>
            </li>
          )}
          {APP_NAV.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={pathname === item.href ? 'page' : undefined}
                className="flex min-h-touch items-center px-4 text-sm font-medium text-ink hover:bg-surface-2"
              >
                {item.label}
              </Link>
            </li>
          ))}
          <li className="border-t border-border-subtle">
            <button
              type="button"
              onClick={() => signOut({ callbackUrl: '/' })}
              className="flex min-h-touch w-full items-center px-4 text-sm font-medium text-ink-muted hover:bg-surface-2"
            >
              로그아웃
            </button>
          </li>
        </ul>
      </nav>
    </header>
  )
}
