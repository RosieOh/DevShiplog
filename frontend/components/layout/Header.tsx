'use client'

import Link from 'next/link'
import { useSession, signOut } from 'next-auth/react'

export default function Header() {
  const { data: session } = useSession()

  return (
    <header className="fixed top-0 w-full flex justify-between items-center px-10 py-5 z-50 backdrop-blur-md bg-white/80 border-b border-black/5">
      <Link href="/" className="flex items-center gap-2 font-bold text-xl tracking-tight text-[#111111]">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L15 8L22 9L17 14L18 21L12 18L6 21L7 14L2 9L9 8L12 2Z" fill="black"/>
        </svg>
        Devshiplog
      </Link>
      <nav className="hidden md:flex items-center gap-8">
        {session && (
          <>
            <Link href="/dashboard" className="text-sm font-medium text-[#111111] hover:text-[#666666] transition-colors">
              Dashboard
            </Link>
            <Link href="/drafts/new" className="text-sm font-medium text-[#111111] hover:text-[#666666] transition-colors">
              새 글 만들기
            </Link>
            <Link href="/onboarding/style" className="text-sm font-medium text-[#111111] hover:text-[#666666] transition-colors">
              Style DNA
            </Link>
          </>
        )}
      </nav>
      <div className="flex items-center gap-4">
        {session ? (
          <>
            <span className="text-sm text-[#666666] hidden md:inline">{session.user?.email}</span>
            <button
              onClick={() => signOut({ callbackUrl: '/' })}
              className="px-5 py-2.5 bg-gray-100 text-[#111111] rounded-full text-sm font-semibold hover:bg-gray-200 transition-colors"
            >
              로그아웃
            </button>
          </>
        ) : (
          <Link
            href="/auth/login"
            className="bg-[#d1fb52] px-5 py-2.5 rounded-full text-sm font-semibold text-black hover:scale-105 transition-transform"
          >
            로그인
          </Link>
        )}
      </div>
    </header>
  )
}
