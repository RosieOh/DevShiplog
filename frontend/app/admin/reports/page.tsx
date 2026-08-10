'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { apiClient } from '@/lib/api/client'

/**
 * 신고 처리 화면.
 *
 * 신고는 쌓이는데 볼 곳이 없으면 신고 기능은 장식이다.
 * 여기서 중요한 건 "빠짐없이 보여주기" 가 아니라 "판단하고 한 번에 끝내기" 다 —
 * 처리에 클릭이 여러 번 들면 운영자는 결국 안 하게 된다.
 */

interface Target {
  kind: string
  title?: string
  status?: string
  excerpt?: string
  url?: string | null
  author?: string | null
  handle?: string
  display_name?: string
}

interface Report {
  id: string
  reason: string
  detail: string
  target_type: string
  target_id: string
  target: Target | null
  created_at: string | null
}

const REASON_LABEL: Record<string, string> = {
  spam: '스팸',
  abuse: '욕설/혐오',
  copyright: '저작권',
  sexual: '음란물',
  other: '기타',
}

function since(iso: string | null): string {
  if (!iso) return ''
  const hours = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
  if (hours < 1) return '방금'
  if (hours < 24) return `${hours}시간 전`
  return `${Math.floor(hours / 24)}일 전`
}

export default function AdminReportsPage() {
  const { status } = useSession()
  const router = useRouter()
  const [reports, setReports] = useState<Report[] | null>(null)
  const [denied, setDenied] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(() => {
    apiClient
      .get<{ items: Report[] }>('/api/v1/admin/reports')
      .then((data) => setReports(data.items))
      .catch(() => {
        // 서버는 권한 없음을 404 로 답한다. 화면의 존재를 광고하지 않기 위해서다.
        setDenied(true)
        setReports([])
      })
  }, [])

  useEffect(() => {
    if (status === 'loading') return
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }
    load()
  }, [status, router, load])

  async function resolve(
    id: string,
    decision: 'resolved' | 'rejected',
    unpublish: boolean,
    suspendDays = 0
  ) {
    setBusy(id)
    try {
      await apiClient.post(`/api/v1/admin/reports/${id}/resolve`, {
        status: decision,
        unpublish_post: unpublish,
        suspend_author_days: suspendDays,
      })
      // 처리한 건은 목록에서 바로 뺀다. 다시 불러오면 위치가 흔들려서
      // 방금 무엇을 처리했는지 알기 어려워진다.
      setReports((prev) => (prev ? prev.filter((r) => r.id !== id) : prev))
    } finally {
      setBusy(null)
    }
  }

  if (reports === null) {
    return (
      <div className="mx-auto max-w-shell px-4 py-12 md:px-6">
        <p className="text-ink-muted">불러오는 중...</p>
      </div>
    )
  }

  if (denied) {
    return (
      <div className="mx-auto max-w-shell px-4 py-12 md:px-6">
        <h1 className="text-2xl font-bold text-ink">페이지를 찾을 수 없습니다</h1>
        <p className="mt-3 text-ink-muted">주소를 다시 확인해 주세요.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-shell px-4 py-8 md:px-6">
      <header className="border-b border-border pb-6">
        <p className="font-mono text-xs uppercase tracking-widest text-ink-faint">운영</p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-ink">신고 처리</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-muted">
          오래된 신고부터 보여줍니다. 신고 내용과 대상 글을 한 화면에서 보고 바로 처리하세요.
        </p>
      </header>

      {reports.length === 0 ? (
        <div className="mt-8 rounded border border-border bg-surface p-8 text-center">
          <p className="text-sm text-ink-muted">처리할 신고가 없습니다.</p>
        </div>
      ) : (
        <ul className="mt-6 space-y-4">
          {reports.map((report) => (
            <li key={report.id} className="rounded border border-border bg-surface p-5">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="rounded bg-stale/12 px-2 py-0.5 text-xs font-bold text-stale">
                  {REASON_LABEL[report.reason] ?? report.reason}
                </span>
                <span className="font-mono text-xs text-ink-faint">
                  {report.target_type} · {since(report.created_at)}
                </span>
              </div>

              {report.detail && (
                <p className="mt-3 text-sm leading-relaxed text-ink">“{report.detail}”</p>
              )}

              {/* 대상 내용을 여기 싣는다. 다시 찾아 들어가야 하면 처리가 느려진다. */}
              {report.target?.kind === 'post' ? (
                <div className="mt-4 rounded border border-border-subtle bg-surface-2 p-4">
                  <p className="text-sm font-bold text-ink">{report.target.title}</p>
                  <p className="mt-1 font-mono text-xs text-ink-faint">
                    @{report.target.author} · {report.target.status}
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ink-muted">
                    {report.target.excerpt}
                  </p>
                  {report.target.url && (
                    <a
                      href={report.target.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-3 inline-block text-sm font-medium text-accent underline underline-offset-2"
                    >
                      원문 보기
                    </a>
                  )}
                </div>
              ) : report.target?.kind === 'user' ? (
                <div className="mt-4 rounded border border-border-subtle bg-surface-2 p-4">
                  <p className="text-sm font-bold text-ink">{report.target.display_name}</p>
                  <p className="mt-1 font-mono text-xs text-ink-faint">@{report.target.handle}</p>
                </div>
              ) : (
                <p className="mt-4 text-sm text-ink-faint">
                  대상이 이미 삭제되었습니다. 반려로 정리하세요.
                </p>
              )}

              <div className="mt-4 flex flex-wrap gap-2 border-t border-border-subtle pt-4">
                <button
                  type="button"
                  disabled={busy === report.id}
                  onClick={() => resolve(report.id, 'rejected', false)}
                  className="min-h-touch rounded border border-border px-4 text-sm font-medium text-ink-muted hover:bg-surface-2 disabled:opacity-50"
                >
                  문제 없음
                </button>
                <button
                  type="button"
                  disabled={busy === report.id}
                  onClick={() => resolve(report.id, 'resolved', false)}
                  className="min-h-touch rounded border border-border px-4 text-sm font-medium text-ink hover:bg-surface-2 disabled:opacity-50"
                >
                  조치함 (글은 유지)
                </button>
                {report.target?.kind === 'post' && (
                  <>
                    <button
                      type="button"
                      disabled={busy === report.id}
                      onClick={() => resolve(report.id, 'resolved', true)}
                      className="min-h-touch rounded bg-stale px-4 text-sm font-bold text-surface hover:opacity-90 disabled:opacity-50"
                    >
                      글 내리기
                    </button>
                    {/*
                      * 반복하는 사람은 글을 하나씩 내리는 것으로 멈추지 않는다.
                      * 여기서 끝낼 수 있어야 한다 — 다시 사용자를 찾아 들어가야 하면
                      * 그 단계에서 그만두게 된다.
                      */}
                    <button
                      type="button"
                      disabled={busy === report.id}
                      onClick={() => {
                        if (
                          confirm(
                            `@${report.target?.author} 를 7일간 정지하고 글을 내립니다.
` +
                              '읽기는 계속 가능하고, 기한이 지나면 저절로 풀립니다.'
                          )
                        ) {
                          resolve(report.id, 'resolved', true, 7)
                        }
                      }}
                      className="min-h-touch rounded border border-stale px-4 text-sm font-bold text-stale hover:bg-stale/8 disabled:opacity-50"
                    >
                      글 내리고 7일 정지
                    </button>
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-8 text-xs leading-relaxed text-ink-faint">
        글 내리기는 글을 비공개(unlisted)로 바꿉니다. 지우지 않으므로 오판이면 되돌릴 수 있습니다.
        정지는 기한제입니다 — 쓰기만 막히고 읽기는 되며, 기한이 지나면 저절로 풀립니다.
        운영 화면에서 바로 해제할 수도 있습니다.
      </p>
    </div>
  )
}
