'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { apiClient } from '@/lib/api/client'
import { useToastStore } from '@/store/toastStore'
import StackBadges from '@/components/blog/StackBadges'
import type { Freshness, PostStack } from '@/lib/api/public'

interface MaintainItem {
  id: string
  title: string
  url: string | null
  view_count: number
  freshness: Freshness
  stacks: PostStack[]
  signals: { works: number; broken: number; my_signal: null }
}

/**
 * 갱신이 필요한 내 글.
 *
 * "낡은 글이 있다" 만으로는 아무도 안 고친다. 무엇부터 고쳐야 하는지가 있어야 한다.
 * 그래서 안 읽히는 낡은 글보다 **읽히는데 안 되는 글**을 위로 올린다.
 */
export default function MaintainPage() {
  const { status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [items, setItems] = useState<MaintainItem[]>([])
  const [loading, setLoading] = useState(true)
  const [verifying, setVerifying] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await apiClient.get<{ items: MaintainItem[] }>('/api/v1/posts/needs-update')
      setItems(data.items)
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '불러오지 못했습니다.',
        type: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [addToast])

  useEffect(() => {
    if (status === 'loading') return
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }
    void load()
  }, [status, router, load])

  const verify = async (id: string) => {
    try {
      setVerifying(id)
      await apiClient.post(`/api/v1/posts/${id}/verify`, {})
      // 목록에서 바로 뺀다. 다시 불러오면 방금 누른 항목이 사라지는 게 안 보인다.
      setItems((current) => current.filter((item) => item.id !== id))
      addToast({ message: '검증 시각을 기록했습니다.', type: 'success' })
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '기록에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setVerifying(null)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-shell px-4 py-12 md:px-6">
        <p className="text-ink-muted">불러오는 중...</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-shell px-4 py-8 md:px-6">
      <header className="border-b border-border pb-6">
        <h1 className="text-2xl font-bold tracking-tight text-ink">글 관리</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-muted">
          기술 글은 시간이 지나면 틀린 글이 됩니다. 다시 돌려보고{' '}
          <b className="font-bold text-ink">지금도 된다</b>고 기록하면, 독자가 이 글을 믿어도
          되는지 판단할 수 있습니다.
        </p>
      </header>

      {items.length === 0 ? (
        <div className="mt-8 rounded border border-fresh/30 bg-fresh/8 px-6 py-16 text-center">
          <p className="font-bold text-fresh">손볼 글이 없습니다.</p>
          <p className="mt-2 text-sm text-ink-muted">
            발행한 글이 모두 최근에 검증되었고, 안 된다는 신고도 없습니다.
          </p>
        </div>
      ) : (
        <ul className="mt-6 space-y-3">
          {items.map((item) => {
            const urgent = item.signals.broken > 0
            return (
              <li
                key={item.id}
                className={`rounded border bg-surface p-4 md:p-5 ${
                  urgent ? 'border-stale/40' : 'border-border'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    {urgent && (
                      <p className="mb-1.5 text-xs font-bold text-stale">
                        {item.signals.broken}명이 “안 됐어요”를 눌렀습니다
                      </p>
                    )}

                    {item.url ? (
                      <Link
                        href={item.url}
                        className="text-base font-bold leading-snug text-ink hover:underline underline-offset-2"
                      >
                        {item.title}
                      </Link>
                    ) : (
                      <span className="text-base font-bold text-ink">{item.title}</span>
                    )}

                    <p className="mt-1.5 text-sm text-ink-muted">{item.freshness.reason}</p>

                    {item.stacks.length > 0 && (
                      <div className="mt-3">
                        <StackBadges stacks={item.stacks} size="compact" />
                      </div>
                    )}

                    <p className="mt-3 font-mono text-xs tabular-nums text-ink-faint">
                      조회 {item.view_count}
                      {item.signals.works > 0 && ` · 잘 됐어요 ${item.signals.works}`}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => void verify(item.id)}
                    disabled={verifying === item.id}
                    className="inline-flex min-h-touch shrink-0 items-center rounded border border-border bg-surface px-4 text-sm font-bold text-ink transition-colors hover:bg-bg disabled:opacity-50"
                  >
                    {verifying === item.id ? '기록 중...' : '다시 확인함'}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}

      <p className="mt-6 text-xs leading-relaxed text-ink-faint">
        내용을 고치지 않아도 “다시 확인함”을 누를 수 있습니다. 다시 돌려봤고 그대로
        됐다는 것 자체가 독자에게 주는 정보입니다.
      </p>
    </div>
  )
}
