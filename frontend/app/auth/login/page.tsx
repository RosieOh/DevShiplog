'use client'

import { useState } from 'react'
import { signIn } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function LoginPage() {
  const router = useRouter()
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isSignUp) {
        // 회원가입
        const response = await fetch('/api/auth/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, name }),
        })

        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.message || '회원가입에 실패했습니다.')
        }

        // 회원가입 성공 후 자동 로그인
        const result = await signIn('credentials', {
          email,
          password,
          redirect: false,
        })

        if (result?.error) {
          setError('로그인에 실패했습니다.')
          return
        }

        router.push('/dashboard')
      } else {
        // 로그인
        const result = await signIn('credentials', {
          email,
          password,
          redirect: false,
        })

        if (result?.error) {
          setError('이메일 또는 비밀번호가 올바르지 않습니다.')
          return
        }

        router.push('/dashboard')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-bg min-h-screen flex items-center justify-center px-[5%]">
      <div className="max-w-md w-full">
        <div className="bg-surface rounded-lg border border-border-subtle p-10">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-ink mb-3 tracking-tight">
              {isSignUp ? '회원가입' : '로그인'}
            </h1>
            <p className="text-ink-muted">
              {isSignUp ? '새 계정을 만들어 시작하세요' : 'Devshiplog에 오신 것을 환영합니다'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {isSignUp && (
              <div>
                <label htmlFor="signup-name" className="block text-sm font-semibold text-ink mb-2">
                  이름
                </label>
                <input
                  id="signup-name"
                  name="name"
                  autoComplete="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full p-4 border border-border rounded bg-bg"
                  placeholder="이름을 입력하세요"
                />
              </div>
            )}

            <div>
              <label htmlFor="auth-email" className="block text-sm font-semibold text-ink mb-2">
                이메일
              </label>
              <input
                id="auth-email"
                name="email"
                autoComplete="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full p-4 border border-border rounded bg-bg"
                placeholder="email@example.com"
              />
            </div>

            <div>
              <label htmlFor="auth-password" className="block text-sm font-semibold text-ink mb-2">
                비밀번호
              </label>
              <input
                id="auth-password"
                name="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                // 백엔드 회원가입 정책과 동일하게 8자 이상
                minLength={isSignUp ? 8 : undefined}
                className="w-full p-4 border border-border rounded bg-bg"
                placeholder={isSignUp ? '8자 이상 입력하세요' : '비밀번호를 입력하세요'}
              />
            </div>

            {error && (
              <div className="p-4 bg-danger/10 border border-danger/30 rounded">
                <p className="text-danger text-sm">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full px-8 py-5 bg-ink text-bg rounded-full transition-opacity hover:opacity-85 font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '처리 중...' : isSignUp ? '회원가입' : '로그인'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setIsSignUp(!isSignUp)
                setError('')
              }}
              className="inline-flex items-center min-h-touch px-2 text-ink-muted hover:text-ink transition-colors text-sm"
            >
              {isSignUp ? '이미 계정이 있으신가요? 로그인' : '계정이 없으신가요? 회원가입'}
            </button>
          </div>

          {/* 로그인 화면에만 둔다. 회원가입 중에는 재설정할 비밀번호가 없다. */}
          {!isSignUp && (
            <div className="mt-2 text-center">
              <Link
                href="/auth/forgot"
                className="inline-flex min-h-touch items-center px-2 text-sm text-ink-muted transition-colors hover:text-ink"
              >
                비밀번호를 잊으셨나요?
              </Link>
            </div>
          )}

          <div className="mt-8 pt-8 border-t border-border">
            <Link
              href="/"
              className="flex items-center justify-center min-h-touch text-ink-muted hover:text-ink transition-colors text-sm"
            >
              ← 홈으로 돌아가기
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

