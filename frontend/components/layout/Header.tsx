'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { useSession, signOut } from 'next-auth/react'
import { CloseIcon, MenuIcon } from '@/components/ui/icons'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/drafts/new', label: '새 글 만들기' },
  { href: '/onboarding/style', label: 'Style DNA' },
]

export default function Header() {
  const { data: session } = useSession()
  const pathname = usePathname()
  const [menuOpen, setMenuOpen] = useState(false)
  const toggleRef = useRef<HTMLButtonElement>(null)

  // 라우트가 바뀌면 메뉴를 닫는다 (모바일에서 열린 채로 남는 문제).
  useEffect(() => setMenuOpen(false), [pathname])

  // Esc 로 빠져나갈 수 있어야 하고, 포커스는 열었던 버튼으로 돌아가야 한다.
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

  const linkClass = (href: string) =>
    `text-sm font-medium transition-colors ${
      pathname === href ? 'text-ink' : 'text-ink-muted hover:text-ink'
    }`

  return (
    <header className="fixed top-0 w-full z-50 backdrop-blur-md bg-surface/85 border-b border-black/5">
      <div className="flex justify-between items-center gap-4 px-5 md:px-10 py-4">
        <Link
          href="/"
          className="flex items-center gap-2 min-h-touch font-bold text-xl tracking-tight text-ink"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 2L15 8L22 9L17 14L18 21L12 18L6 21L7 14L2 9L9 8L12 2Z"
              fill="currentColor"
            />
          </svg>
          Devshiplog
        </Link>

        <nav className="hidden md:flex items-center gap-8" aria-label="주요">
          {session &&
            NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={pathname === item.href ? 'page' : undefined}
                className={linkClass(item.href)}
              >
                {item.label}
              </Link>
            ))}
        </nav>

        <div className="flex items-center gap-2 md:gap-4">
          {session ? (
            <>
              <span className="text-sm text-ink-muted hidden lg:inline">
                {session.user?.email}
              </span>
              <button
                type="button"
                onClick={() => signOut({ callbackUrl: '/' })}
                className="hidden md:inline-flex items-center px-5 py-2.5 bg-canvas border border-black/10 text-ink rounded-full text-sm font-semibold hover:bg-line transition-colors"
              >
                로그아웃
              </button>
              {/* 모바일에서는 네비게이션이 통째로 사라지면 안 되므로 토글로 접는다. */}
              <button
                ref={toggleRef}
                type="button"
                onClick={() => setMenuOpen((open) => !open)}
                aria-expanded={menuOpen}
                aria-controls="mobile-nav"
                aria-label={menuOpen ? '메뉴 닫기' : '메뉴 열기'}
                className="md:hidden grid h-touch w-touch place-items-center rounded-full text-ink hover:bg-canvas transition-colors"
              >
                {menuOpen ? <CloseIcon className="w-6 h-6" /> : <MenuIcon className="w-6 h-6" />}
              </button>
            </>
          ) : (
            <Link
              href="/auth/login"
              className="inline-flex items-center min-h-touch bg-accent px-5 py-2.5 rounded-full text-sm font-semibold text-ink motion-safe:hover:scale-105 transition-transform"
            >
              로그인
            </Link>
          )}
        </div>
      </div>

      {session && (
        <nav
          id="mobile-nav"
          aria-label="주요 (모바일)"
          hidden={!menuOpen}
          className="md:hidden border-t border-black/5 bg-surface px-5 py-3"
        >
          <ul className="flex flex-col">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={pathname === item.href ? 'page' : undefined}
                  className={`flex items-center min-h-touch ${linkClass(item.href)}`}
                >
                  {item.label}
                </Link>
              </li>
            ))}
            <li className="mt-2 pt-3 border-t border-black/5">
              <p className="text-xs text-ink-muted mb-2">{session.user?.email}</p>
              <button
                type="button"
                onClick={() => signOut({ callbackUrl: '/' })}
                className="flex items-center min-h-touch text-sm font-semibold text-ink"
              >
                로그아웃
              </button>
            </li>
          </ul>
        </nav>
      )}
    </header>
  )
}
