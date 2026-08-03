'use client'

import Link from 'next/link'
import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { draftService, Draft } from '@/features/drafts/services/draftService'
import { useToastStore } from '@/store/toastStore'
import { apiClient } from '@/lib/api/client'

interface UsageStats {
  this_month: number
  total: number
  this_week: number
  monthly_quota: number
  /** 무제한이면 -1 */
  remaining: number
  cost_usd_this_month: number
}

const EMPTY_USAGE: UsageStats = {
  this_month: 0,
  total: 0,
  this_week: 0,
  monthly_quota: 0,
  remaining: -1,
  cost_usd_this_month: 0,
}

/** meta_json 은 임의 JSON 이라 title 이 문자열이라는 보장이 없다. */
function draftTitle(draft: Draft): string {
  const title = draft.latest_version?.meta_json?.title
  return typeof title === 'string' && title.trim() ? title : '제목 없음'
}

export default function DashboardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [loading, setLoading] = useState(true)
  const [usageStats, setUsageStats] = useState<UsageStats>(EMPTY_USAGE)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [draftsData, statsData] = await Promise.all([
        draftService.list(),
        apiClient.get<UsageStats>('/api/v1/usage/stats'),
      ])
      setDrafts(draftsData)
      setUsageStats(statsData)
    } catch (error) {
      addToast({
        message: error instanceof Error ? error.message : '데이터를 불러오는데 실패했습니다.',
        type: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [addToast])

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }

    if (status === 'authenticated') {
      void loadData()
    }
  }, [status, router, loadData])

  return (
    <div className="bg-bg min-h-screen">
      <div className="max-w-[1400px] mx-auto px-[5%] py-12">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-5xl font-bold text-ink mb-3 tracking-tight">Dashboard</h1>
          <p className="text-lg text-ink-muted">기술 글 초안을 관리하고 새 글을 만들어보세요</p>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Link
            href="/drafts/new"
            className="bg-surface p-8 rounded-lg border border-border-subtle  transition-transform"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-accent rounded flex items-center justify-center">
                <svg className="w-7 h-7 text-ink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-xl text-ink">새 글 만들기</h3>
                <p className="text-sm text-ink-muted">URL이나 텍스트로부터 초안 생성</p>
              </div>
            </div>
          </Link>

          <Link
            href="/onboarding/style"
            className="bg-surface p-8 rounded-lg border border-border-subtle  transition-transform"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-accent rounded flex items-center justify-center">
                <svg className="w-7 h-7 text-ink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-xl text-ink">Style DNA 설정</h3>
                <p className="text-sm text-ink-muted">블로그 스타일 분석 및 적용</p>
              </div>
            </div>
          </Link>

          <div className="bg-surface p-8 rounded-lg border border-border-subtle">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-accent rounded flex items-center justify-center">
                <svg className="w-7 h-7 text-ink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-xl text-ink">사용량</h3>
                <p className="text-sm text-ink-muted">이번 달: {usageStats.this_month}개 생성</p>
                <p className="text-xs text-ink-muted mt-1">전체: {usageStats.total}개</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Drafts */}
        <div className="bg-surface rounded-lg border border-border-subtle p-10">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-3xl font-bold text-ink tracking-tight">최근 Draft</h2>
            <Link
              href="/drafts/new"
              className="text-ink-muted hover:text-ink font-semibold transition-colors"
            >
              모두 보기 →
            </Link>
          </div>

          {loading ? (
            <div className="text-center py-16">
              <div className="motion-safe:animate-spin motion-reduce:animate-pulse rounded-full h-12 w-12 border-2 border-border border-t-ink mx-auto"></div>
            </div>
          ) : drafts.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-20 h-20 bg-accent rounded flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-ink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-ink-muted mb-6 text-lg">아직 생성된 Draft가 없습니다</p>
              <Link
                href="/drafts/new"
                className="inline-block px-8 py-4 bg-ink text-bg rounded-full font-semibold transition-opacity hover:opacity-85"
              >
                첫 Draft 만들기
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {drafts.map((draft) => (
                <Link
                  key={draft.id}
                  href={`/drafts/${draft.id}/edit`}
                  className="block p-6 border border-border-subtle rounded  transition-transform"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-bold text-xl text-ink mb-2">
                        {draftTitle(draft)}
                      </h3>
                      <p className="text-sm text-ink-muted">
                        {draft.type} · {draft.audience} · {draft.length_preset}
                      </p>
                    </div>
                    <span className={`px-4 py-2 rounded-full text-xs font-semibold ${
                      draft.status === 'active' ? 'bg-ink text-bg' : 'bg-surface-2 text-ink-muted'
                    }`}>
                      {draft.status}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
