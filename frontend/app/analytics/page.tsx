'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { analyticsService, DraftStats, WritingPattern, TimeDistribution } from '@/features/analytics/services/analyticsService'
import { useToastStore } from '@/store/toastStore'
import Link from 'next/link'

export default function AnalyticsPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [stats, setStats] = useState<DraftStats | null>(null)
  const [patterns, setPatterns] = useState<WritingPattern | null>(null)
  const [timeDist, setTimeDist] = useState<TimeDistribution | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }
    if (status === 'authenticated') {
      loadAnalytics()
    }
  }, [status, router])

  const loadAnalytics = async () => {
    try {
      setLoading(true)
      const [statsData, patternsData, timeData] = await Promise.all([
        analyticsService.getDraftStats(),
        analyticsService.getWritingPatterns(),
        analyticsService.getTimeDistribution(),
      ])
      setStats(statsData)
      setPatterns(patternsData)
      setTimeDist(timeData)
    } catch (err: any) {
      addToast({
        message: `통계 로드 실패: ${err.message}`,
        type: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-[#f9f9f7] min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#d1fb52]"></div>
      </div>
    )
  }

  return (
    <div className="bg-[#f9f9f7] min-h-screen">
      <div className="max-w-[1400px] mx-auto px-[5%] py-12">
        <div className="mb-12">
          <Link href="/dashboard" className="text-[#666666] hover:text-[#111111] mb-4 inline-block transition-colors">
            ← Dashboard로 돌아가기
          </Link>
          <h1 className="text-5xl font-bold text-[#111111] tracking-tight">통계 & 분석</h1>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-[32px] border border-black/5 p-6">
            <h3 className="text-sm text-[#666666] mb-2">총 Draft 수</h3>
            <p className="text-4xl font-bold text-[#111111]">{stats?.total || 0}</p>
          </div>
          <div className="bg-white rounded-[32px] border border-black/5 p-6">
            <h3 className="text-sm text-[#666666] mb-2">평균 길이</h3>
            <p className="text-4xl font-bold text-[#111111]">{Math.round(stats?.average_length || 0)}자</p>
          </div>
          <div className="bg-white rounded-[32px] border border-black/5 p-6">
            <h3 className="text-sm text-[#666666] mb-2">Style DNA 사용률</h3>
            <p className="text-4xl font-bold text-[#111111]">{Math.round(stats?.style_profile_usage_rate || 0)}%</p>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-[32px] border border-black/5 p-8">
            <h2 className="text-2xl font-bold mb-6 text-[#111111]">타입별 분포</h2>
            <div className="space-y-3">
              {stats && Object.entries(stats.by_type).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-[#666666]">{type}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-32 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-[#d1fb52] h-2 rounded-full"
                        style={{ width: `${(count / stats.total) * 100}%` }}
                      ></div>
                    </div>
                    <span className="font-semibold text-[#111111] w-8 text-right">{count}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-[32px] border border-black/5 p-8">
            <h2 className="text-2xl font-bold mb-6 text-[#111111]">작성 패턴</h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-[#666666] mb-1">가장 많이 사용한 타입</p>
                <p className="text-lg font-semibold text-[#111111]">{patterns?.most_used_type || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-[#666666] mb-1">가장 많이 사용한 대상</p>
                <p className="text-lg font-semibold text-[#111111]">{patterns?.most_used_audience || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-[#666666] mb-1">선호하는 길이</p>
                <p className="text-lg font-semibold text-[#111111]">{patterns?.preferred_length || '-'}</p>
              </div>
            </div>
          </div>
        </div>

        {timeDist && (
          <div className="bg-white rounded-[32px] border border-black/5 p-8">
            <h2 className="text-2xl font-bold mb-6 text-[#111111]">시간대별 분포</h2>
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-lg font-semibold mb-4 text-[#111111]">시간대별</h3>
                <div className="space-y-2">
                  {Object.entries(timeDist.by_hour)
                    .sort(([a], [b]) => parseInt(a) - parseInt(b))
                    .map(([hour, count]) => (
                      <div key={hour} className="flex items-center justify-between">
                        <span className="text-[#666666]">{hour}시</span>
                        <div className="flex items-center gap-3">
                          <div className="w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-[#d1fb52] h-2 rounded-full"
                              style={{ width: `${(count / Math.max(...Object.values(timeDist.by_hour))) * 100}%` }}
                            ></div>
                          </div>
                          <span className="font-semibold text-[#111111] w-6 text-right">{count}</span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-4 text-[#111111]">요일별</h3>
                <div className="space-y-2">
                  {Object.entries(timeDist.by_day_of_week).map(([day, count]) => (
                    <div key={day} className="flex items-center justify-between">
                      <span className="text-[#666666]">{day}</span>
                      <div className="flex items-center gap-3">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-[#d1fb52] h-2 rounded-full"
                            style={{ width: `${(count / Math.max(...Object.values(timeDist.by_day_of_week))) * 100}%` }}
                          ></div>
                        </div>
                        <span className="font-semibold text-[#111111] w-6 text-right">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

