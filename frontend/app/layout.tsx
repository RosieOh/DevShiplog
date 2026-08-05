import type { Metadata } from 'next'
import { JetBrains_Mono } from 'next/font/google'
import './globals.css'

import Header from '@/components/layout/Header'
import Footer from '@/components/layout/Footer'
import Toast from '@/components/ui/Toast'
import SessionProvider from '@/components/providers/SessionProvider'
import { SITE_NAME, SITE_URL } from '@/lib/api/public'
import { ErrorBoundary } from '@/components/ErrorBoundary'

/*
 * 본문 서체는 OS 시스템 스택을 쓴다 (globals.css).
 * 한글 웹폰트는 수 MB 이고, 한국어 사용자의 OS 에는 이미 좋은 본문 서체가 있다.
 * 코드 블록만 JetBrains Mono 를 내려받는다 — 여기서는 글자 폭이 의미를 가진다.
 */
const mono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  display: 'swap',
  variable: '--font-mono',
})

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — 개발자를 위한 기술 블로그`,
    template: `%s — ${SITE_NAME}`,
  },
  description: 'AI가 초안을 만들고, 내 톤으로 다듬어, 바로 발행하는 기술 블로그 플랫폼',
}

/*
 * 첫 페인트 전에 테마를 확정한다.
 * React 가 붙은 뒤에 적용하면 흰 화면이 번쩍인 뒤 어두워진다.
 */
const THEME_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem('devshiplog-theme');
    var system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', stored || system);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={mono.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        {/* 렌더 중 예외가 나도 흰 화면 대신 복구할 수 있는 화면을 보여준다. */}
        <ErrorBoundary>
          <SessionProvider>
            <a
              href="#main"
              className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded focus:bg-ink focus:px-4 focus:py-2 focus:text-bg"
            >
              본문으로 건너뛰기
            </a>
            <Header />
            <main id="main" className="min-h-[60vh] pt-16">
              {children}
            </main>
            <Footer />
            <Toast />
          </SessionProvider>
        </ErrorBoundary>
      </body>
    </html>
  )
}
