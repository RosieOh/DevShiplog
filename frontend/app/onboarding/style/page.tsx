'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { styleProfileService } from '@/features/style-profiles/services/styleProfileService'
import { useToastStore } from '@/store/toastStore'
import Link from 'next/link'

export default function StyleOnboardingPage() {
  const router = useRouter()
  const { data: session, status } = useSession()
  const { addToast } = useToastStore()
  const [blogUrl, setBlogUrl] = useState('')
  const [sampleCount, setSampleCount] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
    }
  }, [status, router])

  const handleAnalyze = async () => {
    if (!session?.user?.id) {
      addToast({
        message: '로그인이 필요합니다.',
        type: 'error',
      })
      return
    }

    if (!blogUrl.trim()) {
      addToast({
        message: '블로그 주소를 입력해주세요.',
        type: 'error',
      })
      return
    }

    try {
      setLoading(true)
      const profile = await styleProfileService.create({
        blog_url: blogUrl,
        sample_count: sampleCount,
        user_id: session.user.id,
      })
      setResult(profile)
      addToast({
        message: 'Style DNA 생성이 시작되었습니다.',
        type: 'success',
      })
    } catch (err: any) {
      addToast({
        message: `Style DNA 생성 실패: ${err.message}`,
        type: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-[#f9f9f7] min-h-screen">
      <div className="max-w-[1400px] mx-auto px-[5%] py-16">
        <div className="max-w-2xl mx-auto">
          <div className="mb-12">
            <Link href="/dashboard" className="text-[#666666] hover:text-[#111111] mb-6 inline-block transition-colors">
              ← Dashboard로 돌아가기
            </Link>
            <h1 className="text-5xl font-bold text-[#111111] mb-6 tracking-tight">Style DNA 설정</h1>
            <p className="text-lg text-[#666666] leading-relaxed">
              블로그 주소를 입력하면 내 글쓰기 스타일을 분석하여 자동으로 적용합니다.
            </p>
          </div>

          <div className="bg-white rounded-[32px] border border-black/5 p-10">
            <div className="space-y-8">
              <div>
                <label className="block text-sm font-semibold text-[#111111] mb-3">
                  내 블로그 주소
                </label>
                <input
                  type="text"
                  value={blogUrl}
                  onChange={(e) => setBlogUrl(e.target.value)}
                  placeholder="https://velog.io/@username 또는 https://blog.example.com"
                  className="w-full p-5 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] focus:border-transparent bg-[#f9f9f7]"
                />
                <p className="text-sm text-[#666666] mt-3">
                  지원 플랫폼: Velog, Tistory, Medium, WordPress, 기타 RSS 지원 블로그
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-[#111111] mb-3">
                  가져올 글 개수
                </label>
                <input
                  type="number"
                  value={sampleCount}
                  onChange={(e) => setSampleCount(parseInt(e.target.value) || 5)}
                  min={1}
                  max={20}
                  className="w-full p-5 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                />
                <p className="text-sm text-[#666666] mt-3">
                  기본: 5개, 최대: 20개 (더 많은 샘플일수록 정확도가 높아집니다)
                </p>
              </div>

              <div className="p-6 bg-[#d1fb52]/20 border border-[#d1fb52]/30 rounded-2xl">
                <h3 className="font-semibold text-black mb-4">분석 항목</h3>
                <ul className="text-sm text-[#111111] space-y-2">
                  <li>• 톤 (담백/캐주얼/공식)</li>
                  <li>• 종결어미 (~합니다/~해요/~이다)</li>
                  <li>• 구조 선호도 (문제-원인-해결-회고 등)</li>
                  <li>• 코드 블록 사용 빈도</li>
                  <li>• 자주 쓰는 표현</li>
                </ul>
              </div>

              <button
                onClick={handleAnalyze}
                disabled={loading || !blogUrl.trim()}
                className="w-full px-8 py-5 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold text-lg disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {loading ? '분석 중...' : '분석 시작'}
              </button>

              {result && (
                <div className="p-8 bg-[#d1fb52]/20 border border-[#d1fb52]/30 rounded-2xl">
                  <div className="flex items-start gap-6">
                    <div className="flex-shrink-0">
                      <svg className="w-10 h-10 text-[#d1fb52]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <h3 className="font-bold text-black mb-3 text-xl">Style DNA 생성이 시작되었습니다!</h3>
                      <p className="text-[#111111] mb-6">
                        분석이 완료되면 대시보드에서 확인할 수 있습니다.
                      </p>
                      <div className="space-y-2 text-sm text-[#111111] mb-6">
                        <p><strong>상태:</strong> {result.status}</p>
                        <p><strong>Profile ID:</strong> {result.id}</p>
                      </div>
                      <Link
                        href="/dashboard"
                        className="inline-block px-6 py-3 bg-[#111111] text-white rounded-full hover:scale-105 transition-transform font-semibold"
                      >
                        Dashboard로 이동
                      </Link>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
