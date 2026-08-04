'use client'

import { useState } from 'react'
import Link from 'next/link'
import { apiClient } from '@/lib/api/client'

/**
 * 비밀번호 재설정 요청.
 *
 * 성공/실패를 구분해 보여주지 않는다. "가입되지 않은 이메일입니다" 를 띄우면
 * 이 화면이 "이 사람이 우리 서비스를 쓰는가" 를 조회하는 도구가 된다.
 */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await apiClient.post('/api/v1/auth/password-reset', { email })
      setSent(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : '요청에 실패했습니다.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-12">
      <h1 className="text-2xl font-bold text-ink">비밀번호 재설정</h1>

      {sent ? (
        <div className="mt-6 rounded border border-border bg-surface p-6">
          <p className="text-sm leading-relaxed text-ink">
            가입된 주소라면 재설정 링크를 보냈습니다. 메일함을 확인해주세요.
          </p>
          <p className="mt-3 text-sm text-ink-muted">
            메일이 오지 않으면 스팸함을 확인하거나 주소를 다시 확인해주세요.
          </p>
          <Link
            href="/auth/login"
            className="mt-6 inline-flex min-h-touch items-center text-sm font-bold text-ink hover:underline underline-offset-4"
          >
            로그인으로 돌아가기
          </Link>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <p className="text-sm leading-relaxed text-ink-muted">
            가입할 때 쓴 이메일을 입력하면 재설정 링크를 보내드립니다.
          </p>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-ink">
              이메일
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-2 min-h-touch w-full rounded border border-border bg-bg px-4 text-ink"
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || !email}
            className="inline-flex min-h-touch w-full items-center justify-center rounded bg-ink px-6 font-bold text-bg transition-opacity hover:opacity-85 disabled:opacity-50"
          >
            {busy ? '보내는 중...' : '재설정 링크 받기'}
          </button>

          <Link
            href="/auth/login"
            className="flex min-h-touch items-center justify-center text-sm text-ink-muted hover:text-ink"
          >
            로그인으로 돌아가기
          </Link>
        </form>
      )}
    </div>
  )
}
