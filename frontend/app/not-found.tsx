'use client'

import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="bg-[#f9f9f7] min-h-screen flex items-center justify-center px-[5%]">
      <div className="max-w-2xl w-full text-center">
        <div className="mb-8">
          <h1 className="text-9xl font-bold text-[#d1fb52] mb-4">404</h1>
          <h2 className="text-4xl font-bold text-[#111111] mb-4">페이지를 찾을 수 없습니다</h2>
          <p className="text-lg text-[#666666] mb-8">
            요청하신 페이지가 존재하지 않거나 이동되었을 수 있습니다.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/"
            className="px-8 py-4 bg-[#d1fb52] text-black rounded-full font-semibold hover:scale-105 transition-transform"
          >
            홈으로 돌아가기
          </Link>
          <Link
            href="/dashboard"
            className="px-8 py-4 bg-white text-[#111111] border border-black/10 rounded-full font-semibold hover:scale-105 transition-transform"
          >
            Dashboard로 가기
          </Link>
        </div>
      </div>
    </div>
  )
}

