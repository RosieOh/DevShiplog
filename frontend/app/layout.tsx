import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

import Header from '@/components/layout/Header'
import Footer from '@/components/layout/Footer'
import Toast from '@/components/ui/Toast'
import SessionProvider from '@/components/providers/SessionProvider'

// next/font 가 폰트를 셀프 호스팅하므로 Google Fonts <link> 는 필요 없다.
// (중복 요청 + 렌더 블로킹을 유발한다)
const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '600', '700'],
  display: 'swap',
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
    <html lang="ko">
      <body className={inter.className}>
        <SessionProvider>
          <div className="flex flex-col min-h-screen">
            <Header />
            <main className="flex-grow pt-20">{children}</main>
            <Footer />
            <Toast />
          </div>
        </SessionProvider>
      </body>
    </html>
  )
}
