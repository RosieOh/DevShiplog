'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { apiClient } from '@/lib/api/client'

/**
 * 운영 개요.
 *
 * "서버에서 500 이 나도 아무도 모른다" 를 없애려면 어딘가에 보여야 한다.
 * 대시보드를 크게 만드는 것보다 지금 손댈 일이 있는지가 한눈에 보이는 게 먼저다.
 */

interface Summary {
  pending_reports: number
  error_groups: number
  error_events: number
}

interface Suspended {
  handle: string
  display_name: string | null
  suspended_until: string
  reason: string
}

interface ErrorGroup {
  fingerprint: string
  type: string
  message: string
  origin: string
  path: string | null
  method: string | null
  count: number
  first_seen: string
  last_seen: string
  last_request_id: string | null
  resolved_at: string | null
  traceback: string
}

interface Check {
  name: string
  ok: boolean
  required: boolean
  ms: number
  error?: string
}

interface Heartbeat {
  configured: boolean
  last_success: string | null
  last_failure: string | null
  last_error: string | null
  sent: number
}

const CHECK_LABEL: Record<string, string> = {
  database: '데이터베이스',
  redis: 'Redis',
  storage: '파일 저장소',
}

function when(iso: string): string {
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000)
  if (minutes < 1) return '방금'
  if (minutes < 60) return `${minutes}분 전`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}시간 전`
  return `${Math.floor(minutes / 1440)}일 전`
}

export default function AdminPage() {
  const { status } = useSession()
  const router = useRouter()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [errors, setErrors] = useState<{ items: ErrorGroup[]; alerting: boolean } | null>(null)
  const [suspended, setSuspended] = useState<Suspended[]>([])
  const [checks, setChecks] = useState<Check[] | null>(null)
  const [heartbeat, setHeartbeat] = useState<Heartbeat | null>(null)
  const [denied, setDenied] = useState(false)
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'loading') return
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }
    Promise.all([
      apiClient.get<Summary>('/api/v1/admin/summary'),
      apiClient.get<{ items: ErrorGroup[]; alerting: boolean }>('/api/v1/admin/errors'),
      apiClient.get<{ checks: Check[]; heartbeat: Heartbeat }>('/api/v1/admin/readiness'),
      apiClient.get<{ items: Suspended[] }>('/api/v1/admin/users/suspended'),
    ])
      .then(([s, e, r, u]) => {
        setSummary(s)
        setErrors(e)
        setChecks(r.checks)
        setHeartbeat(r.heartbeat)
        setSuspended(u.items)
      })
      // 서버는 권한 없음을 404 로 답한다. 화면의 존재를 광고하지 않기 위해서다.
      .catch(() => setDenied(true))
  }, [status, router])

  async function resolveError(fingerprint: string) {
    await apiClient.post(`/api/v1/admin/errors/${fingerprint}/resolve`, {})
    // 목록에서 바로 뺀다. 다시 불러오면 위치가 흔들려 방금 무엇을 처리했는지 알기 어렵다.
    setErrors((prev) =>
      prev ? { ...prev, items: prev.items.filter((e) => e.fingerprint !== fingerprint) } : prev
    )
    setSummary((prev) => (prev ? { ...prev, error_groups: prev.error_groups - 1 } : prev))
  }

  async function unsuspend(handle: string) {
    await apiClient.post(`/api/v1/admin/users/${handle}/unsuspend`, {})
    setSuspended((prev) => prev.filter((u) => u.handle !== handle))
  }

  if (denied) {
    return (
      <div className="mx-auto max-w-shell px-4 py-12 md:px-6">
        <h1 className="text-2xl font-bold text-ink">페이지를 찾을 수 없습니다</h1>
        <p className="mt-3 text-ink-muted">주소를 다시 확인해 주세요.</p>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="mx-auto max-w-shell px-4 py-12 md:px-6">
        <p className="text-ink-muted">불러오는 중...</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-shell px-4 py-8 md:px-6">
      <header className="border-b border-border pb-6">
        <p className="font-mono text-xs uppercase tracking-widest text-ink-faint">운영</p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-ink">지금 손댈 일</h1>
      </header>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Link
          href="/admin/reports"
          className="rounded border border-border bg-surface p-5 transition-colors hover:bg-surface-2"
        >
          <p className="text-xs font-bold uppercase tracking-wider text-ink-faint">밀린 신고</p>
          <p className="mt-3 font-mono text-3xl font-bold tabular-nums text-ink">
            {summary.pending_reports}
          </p>
          <p className="mt-3 text-sm text-accent">처리하러 가기 →</p>
        </Link>

        <div className="rounded border border-border bg-surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-ink-faint">최근 오류</p>
          <p className="mt-3 font-mono text-3xl font-bold tabular-nums text-ink">
            {summary.error_groups}
          </p>
          <p className="mt-3 font-mono text-xs tabular-nums text-ink-faint">
            총 {summary.error_events}회 발생
          </p>
        </div>
      </div>

      {/* 의존성 상태 — /health 가 healthy 라고 답해도 DB 는 끊겨 있을 수 있다. */}
      <section className="mt-8">
        <h2 className="text-sm font-bold uppercase tracking-wider text-ink-faint">의존성</h2>
        <ul className="mt-3 divide-y divide-border-subtle rounded border border-border bg-surface">
          {(checks ?? []).map((check) => (
            <li key={check.name} className="flex items-center gap-3 px-5 py-3">
              <span
                aria-hidden="true"
                className={`h-2 w-2 shrink-0 rounded-full ${
                  check.ok ? 'bg-fresh' : check.required ? 'bg-stale' : 'bg-aging'
                }`}
              />
              <span className="text-sm font-medium text-ink">
                {CHECK_LABEL[check.name] ?? check.name}
              </span>
              <span className="font-mono text-xs text-ink-faint">
                {check.ok ? `${check.ms}ms` : check.error}
              </span>
              {!check.required && (
                <span className="ml-auto font-mono text-xs text-ink-faint">
                  없어도 서비스는 됨
                </span>
              )}
            </li>
          ))}
        </ul>
        {/*
          * 하트비트가 안 돌면 "서버가 죽어도 아무도 모르는" 상태로 돌아간다.
          * 이 화면은 서버가 살아 있어야 보이므로, 여기서 확인할 수 있는 건
          * "장치가 걸려 있는가" 까지다. 그것만으로도 안 걸어 둔 것과는 다르다.
          */}
        {heartbeat && !heartbeat.configured && (
          <p className="mt-3 rounded border border-aging/40 bg-aging/8 px-4 py-3 text-xs leading-relaxed text-ink">
            하트비트가 꺼져 있습니다. 프로세스가 죽거나 기계가 꺼지면 알림도 함께 멈춰서
            아무 연락도 오지 않습니다. <code className="mx-1 font-mono">HEARTBEAT_URL</code>
            을 설정하세요 (Healthchecks.io 등).
          </p>
        )}
        {heartbeat?.configured && (
          <p className="mt-3 text-xs leading-relaxed text-ink-faint">
            하트비트 {heartbeat.sent}회 전송
            {heartbeat.last_success &&
              ` · 마지막 성공 ${new Date(heartbeat.last_success).toLocaleString('ko-KR')}`}
            {heartbeat.last_error && ` · ${heartbeat.last_error}`}
          </p>
        )}
      </section>

      {/* 걸어 놓고 잊는 것을 막는다. 기한이 지난 정지는 저절로 풀리므로 나오지 않는다. */}
      {suspended.length > 0 && (
        <section className="mt-8">
          <h2 className="text-sm font-bold uppercase tracking-wider text-ink-faint">
            정지 중인 사용자
          </h2>
          <ul className="mt-3 divide-y divide-border-subtle rounded border border-border bg-surface">
            {suspended.map((user) => (
              <li key={user.handle} className="flex flex-wrap items-center gap-3 px-5 py-3">
                <span className="text-sm font-medium text-ink">@{user.handle}</span>
                <span className="font-mono text-xs text-ink-faint">
                  {new Date(user.suspended_until).toLocaleDateString('ko-KR')}까지
                </span>
                {user.reason && (
                  <span className="text-xs text-ink-muted">— {user.reason}</span>
                )}
                <button
                  type="button"
                  onClick={() => unsuspend(user.handle)}
                  className="ml-auto min-h-touch rounded border border-border px-4 text-sm font-medium text-ink hover:bg-surface-2"
                >
                  해제
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-8">
        <h2 className="text-sm font-bold uppercase tracking-wider text-ink-faint">서버 오류</h2>
        {errors && errors.items.length === 0 ? (
          <p className="mt-3 rounded border border-border bg-surface p-8 text-center text-sm text-ink-muted">
            기록된 오류가 없습니다.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {errors?.items.map((group) => (
              <li key={group.fingerprint} className="rounded border border-border bg-surface">
                <button
                  type="button"
                  onClick={() => setOpen(open === group.fingerprint ? null : group.fingerprint)}
                  aria-expanded={open === group.fingerprint}
                  className="flex w-full items-start gap-3 px-5 py-4 text-left hover:bg-surface-2"
                >
                  <span className="mt-0.5 rounded bg-stale/12 px-2 py-0.5 font-mono text-xs font-bold text-stale">
                    ×{group.count}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-mono text-sm font-bold text-ink">
                      {group.type}
                    </span>
                    <span className="mt-0.5 block truncate text-sm text-ink-muted">
                      {group.message}
                    </span>
                    <span className="mt-1 block font-mono text-xs text-ink-faint">
                      {group.method} {group.path} · {when(group.last_seen)}
                    </span>
                  </span>
                </button>
                {open === group.fingerprint && (
                  <div className="border-t border-border-subtle">
                    <pre className="overflow-x-auto bg-surface-2 px-5 py-4 font-mono text-xs leading-relaxed text-ink-muted">
                      {group.traceback}
                    </pre>
                    <div className="flex items-center gap-3 px-5 py-3">
                      <button
                        type="button"
                        onClick={() => resolveError(group.fingerprint)}
                        className="min-h-touch rounded border border-border px-4 text-sm font-medium text-ink hover:bg-surface-2"
                      >
                        확인함
                      </button>
                      <span className="text-xs text-ink-faint">
                        기록은 남습니다. 다시 나면 목록으로 돌아옵니다.
                      </span>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {/*
          * 알림이 꺼져 있으면 그 사실이 보여야 한다.
          * 안 그러면 "오류가 나면 연락이 오겠지" 라고 믿은 채로 아무 연락도 안 온다.
          */}
        {errors && !errors.alerting && (
          <p className="mt-3 rounded border border-aging/40 bg-aging/8 px-4 py-3 text-xs leading-relaxed text-ink">
            알림 통로가 설정돼 있지 않습니다. 새 오류가 나도 이 화면에 들어와야만 알 수 있습니다.
            <code className="mx-1 font-mono">ALERT_EMAIL</code> 또는
            <code className="mx-1 font-mono">ALERT_WEBHOOK_URL</code> 을 설정하세요.
          </p>
        )}
      </section>
    </div>
  )
}
