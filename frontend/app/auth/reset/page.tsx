'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api/client'

const MIN_PASSWORD = 8

function ResetForm() {
  const router = useRouter()
  const token = useSearchParams().get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  // 서버에 보내기 전에 여기서 걸러 준다. 왕복 한 번을 아끼는 게 아니라,
  // 오타를 즉시 알려주는 쪽이 사용자에게 낫다.
  const tooShort = password.length > 0 && password.length < MIN_PASSWORD
  const mismatch = confirm.length > 0 && password !== confirm
  const canSubmit = Boolean(token) && password.length >= MIN_PASSWORD && password === confirm

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await apiClient.post('/api/v1/auth/password-reset/confirm', {
        token,
        new_password: password,
      })
      setDone(true)
      setTimeout(() => router.push('/auth/login'), 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : '변경에 실패했습니다.')
    } finally {
      setBusy(false)
    }
  }

  if (!token) {
    return (
      <div className="rounded border border-border bg-surface p-6">
        <p className="text-sm text-ink">잘못된 링크입니다. 재설정을 다시 요청해주세요.</p>
        <Link
          href="/auth/forgot"
          className="mt-4 inline-flex min-h-touch items-center text-sm font-bold text-ink hover:underline underline-offset-4"
        >
          재설정 다시 요청하기
        </Link>
      </div>
    )
  }

  if (done) {
    return (
      <div className="rounded border border-border bg-surface p-6">
        <p className="text-sm text-ink">비밀번호를 변경했습니다. 로그인 화면으로 이동합니다.</p>
      </div>
    )
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-ink">
          새 비밀번호
        </label>
        <input
          id="password"
          type="password"
          required
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-invalid={tooShort || undefined}
          aria-describedby={tooShort ? 'password-help' : undefined}
          className="mt-2 min-h-touch w-full rounded border border-border bg-bg px-4 text-ink"
        />
        {tooShort && (
          <p id="password-help" className="mt-1.5 text-sm text-danger">
            {MIN_PASSWORD}자 이상이어야 합니다.
          </p>
        )}
      </div>

      <div>
        <label htmlFor="confirm" className="block text-sm font-medium text-ink">
          새 비밀번호 확인
        </label>
        <input
          id="confirm"
          type="password"
          required
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          aria-invalid={mismatch || undefined}
          aria-describedby={mismatch ? 'confirm-help' : undefined}
          className="mt-2 min-h-touch w-full rounded border border-border bg-bg px-4 text-ink"
        />
        {mismatch && (
          <p id="confirm-help" className="mt-1.5 text-sm text-danger">
            두 비밀번호가 다릅니다.
          </p>
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={busy || !canSubmit}
        className="inline-flex min-h-touch w-full items-center justify-center rounded bg-ink px-6 font-bold text-bg transition-opacity hover:opacity-85 disabled:opacity-50"
      >
        {busy ? '변경 중...' : '비밀번호 변경'}
      </button>
    </form>
  )
}

export default function ResetPasswordPage() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-12">
      <h1 className="mb-6 text-2xl font-bold text-ink">새 비밀번호 설정</h1>
      {/* useSearchParams 는 서스펜스 경계가 필요하다 (없으면 페이지 전체가 CSR 로 떨어진다). */}
      <Suspense fallback={<p className="text-sm text-ink-muted">불러오는 중...</p>}>
        <ResetForm />
      </Suspense>
    </div>
  )
}
