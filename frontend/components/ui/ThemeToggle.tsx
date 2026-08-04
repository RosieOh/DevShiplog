'use client'

import { useEffect, useState } from 'react'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'devshiplog-theme'

/**
 * 라이트/다크 전환.
 *
 * 첫 페인트 전에 테마가 정해져야 하므로 실제 적용은 layout.tsx 의 인라인
 * 스크립트가 담당한다. 이 컴포넌트는 그 값을 읽어와 토글만 한다.
 */
export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null)

  useEffect(() => {
    const current = document.documentElement.getAttribute('data-theme')
    setTheme(current === 'dark' ? 'dark' : 'light')
  }, [])

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.setAttribute('data-theme', next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // 시크릿 모드 등에서 저장이 막혀도 이번 세션 전환은 동작해야 한다.
    }
    setTheme(next)
  }

  // 서버 렌더 시점에는 사용자의 테마를 알 수 없다. 마운트 전에는 아이콘을
  // 비워 두어 서버·클라이언트 마크업이 어긋나지 않게 한다.
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? '라이트 모드로 전환' : '다크 모드로 전환'}
      className="grid h-touch w-touch place-items-center rounded-full text-ink transition-colors hover:bg-surface-2"
    >
      {theme === null ? (
        <span className="block h-5 w-5" />
      ) : isDark ? (
        <svg
          className="h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.75}
          strokeLinecap="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
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
          <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z" />
        </svg>
      )}
    </button>
  )
}
