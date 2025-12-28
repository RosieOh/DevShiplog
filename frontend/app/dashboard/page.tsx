'use client'

import Link from 'next/link'
import { useState, useEffect, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { draftService, Draft } from '@/features/drafts/services/draftService'
import { useToastStore } from '@/store/toastStore'
import { apiClient } from '@/lib/api/client'

interface UsageStats {
  this_month: number
  total: number
  this_week: number
}

type SortOption = 'newest' | 'oldest' | 'title'
type FilterType = 'all' | 'troubleshooting' | 'implementation' | 'retrospective' | 'tutorial' | 'release'

export default function DashboardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [loading, setLoading] = useState(true)
  const [usageStats, setUsageStats] = useState<UsageStats>({ this_month: 0, total: 0, this_week: 0 })
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('newest')
  const [filterType, setFilterType] = useState<FilterType>('all')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }

    if (status === 'authenticated') {
      loadData()
    }
  }, [status, router])

  const loadData = async () => {
    try {
      setLoading(true)
      const [draftsData, statsData] = await Promise.all([
        draftService.list(),
        apiClient.get<UsageStats>('/api/v1/usage/stats'),
      ])
      setDrafts(draftsData)
      setUsageStats(statsData)
    } catch (error: any) {
      addToast({
        message: '데이터를 불러오는데 실패했습니다.',
        type: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (draftId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (!confirm('이 Draft를 삭제하시겠습니까?')) {
      return
    }

    try {
      setDeletingId(draftId)
      await draftService.delete(draftId)
      addToast({
        message: 'Draft가 삭제되었습니다.',
        type: 'success',
      })
      await loadData()
    } catch (error: any) {
      addToast({
        message: `삭제 실패: ${error.message}`,
        type: 'error',
      })
    } finally {
      setDeletingId(null)
    }
  }

  // 필터링 및 정렬된 Draft 목록
  const filteredAndSortedDrafts = useMemo(() => {
    let filtered = drafts

    // 검색 필터
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(draft => {
        const title = draft.latest_version?.meta_json?.title || ''
        const content = draft.latest_version?.content_md || ''
        return title.toLowerCase().includes(query) || content.toLowerCase().includes(query)
      })
    }

    // 타입 필터
    if (filterType !== 'all') {
      filtered = filtered.filter(draft => draft.type === filterType)
    }

    // 정렬
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          // 최신순 (created_at이 없으므로 id 기준으로 대략 추정)
          return b.id.localeCompare(a.id)
        case 'oldest':
          return a.id.localeCompare(b.id)
        case 'title':
          const titleA = a.latest_version?.meta_json?.title || ''
          const titleB = b.latest_version?.meta_json?.title || ''
          return titleA.localeCompare(titleB)
        default:
          return 0
      }
    })

    return sorted
  }, [drafts, searchQuery, filterType, sortBy])

  return (
    <div className="bg-[#f9f9f7] min-h-screen">
      <div className="max-w-[1400px] mx-auto px-[5%] py-12">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-5xl font-bold text-[#111111] mb-3 tracking-tight">Dashboard</h1>
          <p className="text-lg text-[#666666]">기술 글 초안을 관리하고 새 글을 만들어보세요</p>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Link
            href="/drafts/new"
            className="bg-white p-8 rounded-[32px] border border-black/5 hover:-translate-y-2 transition-transform"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-[#d1fb52] rounded-2xl flex items-center justify-center">
                <svg className="w-7 h-7 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-xl text-[#111111]">새 글 만들기</h3>
                <p className="text-sm text-[#666666]">URL이나 텍스트로부터 초안 생성</p>
              </div>
            </div>
          </Link>

          <Link
            href="/onboarding/style"
            className="bg-white p-8 rounded-[32px] border border-black/5 hover:-translate-y-2 transition-transform"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-[#d1fb52] rounded-2xl flex items-center justify-center">
                <svg className="w-7 h-7 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-xl text-[#111111]">Style DNA 설정</h3>
                <p className="text-sm text-[#666666]">블로그 스타일 분석 및 적용</p>
              </div>
            </div>
          </Link>

          <Link
            href="/templates"
            className="bg-white p-8 rounded-[32px] border border-black/5 hover:-translate-y-2 transition-transform"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-[#d1fb52] rounded-2xl flex items-center justify-center">
                <svg className="w-7 h-7 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-xl text-[#111111]">템플릿</h3>
                <p className="text-sm text-[#666666]">저장된 템플릿 관리</p>
              </div>
            </div>
          </Link>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-12">
          <Link
            href="/analytics"
            className="bg-white p-8 rounded-[32px] border border-black/5 hover:-translate-y-2 transition-transform"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-[#d1fb52] rounded-2xl flex items-center justify-center">
                <svg className="w-7 h-7 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-xl text-[#111111]">통계 & 분석</h3>
                <p className="text-sm text-[#666666]">작성 패턴 및 통계 확인</p>
              </div>
            </div>
          </Link>

          <div className="bg-white p-8 rounded-[32px] border border-black/5">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-[#d1fb52] rounded-2xl flex items-center justify-center">
                <svg className="w-7 h-7 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-xl text-[#111111]">사용량</h3>
                <p className="text-sm text-[#666666]">이번 달: {usageStats.this_month}개 생성</p>
                <p className="text-xs text-[#666666] mt-1">전체: {usageStats.total}개</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Drafts */}
        <div className="bg-white rounded-[32px] border border-black/5 p-10">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-3xl font-bold text-[#111111] tracking-tight">최근 Draft</h2>
            <Link
              href="/drafts/new"
              className="text-[#666666] hover:text-[#111111] font-semibold transition-colors"
            >
              새로 만들기 →
            </Link>
          </div>

          {/* 검색 및 필터 */}
          <div className="mb-8 space-y-4">
            {/* 검색 바 */}
            <div className="relative">
              <input
                type="text"
                placeholder="Draft 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full p-4 pl-12 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] focus:border-transparent bg-[#f9f9f7]"
              />
              <svg
                className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#666666]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>

            {/* 필터 및 정렬 */}
            <div className="flex flex-wrap gap-4">
              {/* 타입 필터 */}
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value as FilterType)}
                className="px-4 py-2 border border-black/10 rounded-xl bg-white focus:ring-2 focus:ring-[#d1fb52] focus:border-transparent"
              >
                <option value="all">모든 타입</option>
                <option value="troubleshooting">트러블슈팅</option>
                <option value="implementation">구현기</option>
                <option value="retrospective">회고</option>
                <option value="tutorial">튜토리얼</option>
                <option value="release">릴리즈노트</option>
              </select>

              {/* 정렬 */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="px-4 py-2 border border-black/10 rounded-xl bg-white focus:ring-2 focus:ring-[#d1fb52] focus:border-transparent"
              >
                <option value="newest">최신순</option>
                <option value="oldest">오래된순</option>
                <option value="title">제목순</option>
              </select>

              {/* 결과 개수 */}
              <div className="ml-auto flex items-center text-sm text-[#666666]">
                {filteredAndSortedDrafts.length}개 표시
              </div>
            </div>
          </div>

          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-6 border border-black/5 rounded-2xl animate-pulse">
                  <div className="h-6 bg-gray-200 rounded w-3/4 mb-3"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              ))}
            </div>
          ) : filteredAndSortedDrafts.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-20 h-20 bg-[#d1fb52] rounded-2xl flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-[#666666] mb-6 text-lg">
                {searchQuery || filterType !== 'all' 
                  ? '검색 결과가 없습니다' 
                  : '아직 생성된 Draft가 없습니다'}
              </p>
              {!searchQuery && filterType === 'all' && (
                <Link
                  href="/drafts/new"
                  className="inline-block px-8 py-4 bg-[#d1fb52] text-black rounded-full font-semibold hover:scale-105 transition-transform"
                >
                  첫 Draft 만들기
                </Link>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredAndSortedDrafts.map((draft) => (
                <div
                  key={draft.id}
                  className="group relative p-6 border border-black/5 rounded-2xl hover:-translate-y-1 transition-transform"
                >
                  <Link
                    href={`/drafts/${draft.id}/edit`}
                    className="block"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-bold text-xl text-[#111111] mb-2">
                          {draft.latest_version?.meta_json?.title || '제목 없음'}
                        </h3>
                        <p className="text-sm text-[#666666]">
                          {draft.type} · {draft.audience} · {draft.length_preset}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`px-4 py-2 rounded-full text-xs font-semibold ${
                          draft.status === 'active' ? 'bg-[#d1fb52] text-black' : 'bg-gray-100 text-[#666666]'
                        }`}>
                          {draft.status}
                        </span>
                        <button
                          onClick={(e) => handleDelete(draft.id, e)}
                          disabled={deletingId === draft.id}
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-2 hover:bg-red-50 rounded-lg text-red-600 disabled:opacity-50"
                          title="삭제"
                        >
                          {deletingId === draft.id ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                          ) : (
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </div>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
