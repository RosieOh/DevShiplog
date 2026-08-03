import type { Metadata } from 'next'
import { IBM_Plex_Sans, JetBrains_Mono } from 'next/font/google'
import './globals.css'

import Header from '@/components/layout/Header'
import Footer from '@/components/layout/Footer'
import Toast from '@/components/ui/Toast'
import SessionProvider from '@/components/providers/SessionProvider'

/*
 * next/font 가 폰트를 셀프 호스팅하므로 Google Fonts <link> 는 필요 없다
 * (중복 요청 + 렌더 블로킹을 유발한다).
 *
 * Inter 대신 IBM Plex Sans + JetBrains Mono 조합을 쓴다.
 * 글을 쓰고 코드 블록을 다루는 도구라 본문 sans 와 코드 mono 가 한 세트로 설계된
 * 페어링이 맞고, Inter 는 이 카테고리에서 지나치게 흔해 성격이 드러나지 않는다.
 */
const sans = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-sans',
})

const mono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  display: 'swap',
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'Devshiplog - 기술 글 초안 생성 플랫폼',
  description:
    'URL/PR/로그를 넣으면, 내 블로그 톤으로 기술 글 초안을 생성하고 안전/SEO 검수까지 마친 뒤 발행까지 이어주는 플랫폼',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <SessionProvider>
          <div className="flex flex-col min-h-screen">
            <Header />
            {/* 키보드 사용자가 헤더를 매번 지나치지 않도록 건너뛰기 링크를 둔다. */}
            <a
              href="#main"
              className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-canvas"
            >
              본문으로 건너뛰기
            </a>
            <main id="main" className="flex-grow pt-20">
              {children}
            </main>
            <Footer />
            <Toast />
          </div>
        </SessionProvider>
      </body>
    </html>
  )
}
