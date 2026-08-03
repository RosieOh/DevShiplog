'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import {
  styleProfileService,
  StyleProfileResponse,
} from '@/features/style-profiles/services/styleProfileService'
import { useToastStore } from '@/store/toastStore'
import Link from 'next/link'

const POLL_INTERVAL_MS = 3000

export default function StyleOnboardingPage() {
  const router = useRouter()
  const { status } = useSession()
  const { addToast } = useToastStore()
  const [blogUrl, setBlogUrl] = useState('')
  const [sampleCount, setSampleCount] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<StyleProfileResponse | null>(null)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
    }
  }, [status, router])

  // 분석이 끝날 때까지 상태를 폴링한다 (기존에는 시작만 알리고 끝났다).
  useEffect(() => {
    if (!result || result.status === 'succeeded' || result.status === 'failed') return

    const timer = setInterval(async () => {
      try {
        const latest = await styleProfileService.get(result.id)
        setResult(latest)
        if (latest.status === 'succeeded') {
          addToast({ message: 'Style DNA 분석이 완료되었습니다.', type: 'success' })
        } else if (latest.status === 'failed') {
          addToast({ message: latest.error_text || '분석에 실패했습니다.', type: 'error' })
        }
      } catch {
        // 일시적 오류는 다음 폴링에서 다시 시도한다.
      }
    }, POLL_INTERVAL_MS)

    return () => clearInterval(timer)
  }, [result, addToast])

  const handleAnalyze = async () => {
    if (!blogUrl.trim()) {
      addToast({ message: '블로그 주소를 입력해주세요.', type: 'error' })
      return
    }

    try {
      setLoading(true)
      const profile = await styleProfileService.create({
        blog_url: blogUrl.trim(),
        sample_count: sampleCount,
      })
      setResult(profile)
      addToast({ message: 'Style DNA 생성이 시작되었습니다.', type: 'success' })
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : 'Style DNA 생성에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  const statusLabel: Record<StyleProfileResponse['status'], string> = {
    queued: '대기 중',
    running: '분석 중',
    succeeded: '완료',
    failed: '실패',
  }

  return (
    <div className="bg-canvas min-h-screen">
      <div className="max-w-[1400px] mx-auto px-[5%] py-16">
        <div className="max-w-2xl mx-auto">
          <div className="mb-12">
            <Link href="/dashboard" className="text-ink-muted hover:text-ink mb-6 inline-block transition-colors">
              ← Dashboard로 돌아가기
            </Link>
            <h1 className="text-5xl font-bold text-ink mb-6 tracking-tight">Style DNA 설정</h1>
            <p className="text-lg text-ink-muted leading-relaxed">
              블로그 주소를 입력하면 내 글쓰기 스타일을 분석하여 자동으로 적용합니다.
            </p>
          </div>

          <div className="bg-surface rounded-[32px] border border-black/5 p-10">
            <div className="space-y-8">
              <div>
                <label htmlFor="blog-url" className="block text-sm font-semibold text-ink mb-3">
                  내 블로그 주소
                </label>
                <input
                  id="blog-url"
                  name="blogUrl"
                  type="url"
                  inputMode="url"
                  aria-describedby="blog-url-hint"
                  value={blogUrl}
                  onChange={(e) => setBlogUrl(e.target.value)}
                  placeholder="https://velog.io/@username 또는 https://blog.example.com"
                  className="w-full p-5 border border-black/10 rounded-2xl bg-canvas"
                />
                <p id="blog-url-hint" className="text-sm text-ink-muted mt-3">
                  지원 플랫폼: Velog, Tistory, Medium, WordPress, 기타 RSS 지원 블로그
                </p>
              </div>

              <div>
                <label htmlFor="sample-count" className="block text-sm font-semibold text-ink mb-3">
                  가져올 글 개수
                </label>
                <input
                  id="sample-count"
                  name="sampleCount"
                  aria-describedby="sample-count-hint"
                  type="number"
                  value={sampleCount}
                  onChange={(e) => setSampleCount(parseInt(e.target.value) || 5)}
                  min={1}
                  max={20}
                  className="w-full p-5 border border-black/10 rounded-2xl bg-canvas"
                />
                <p id="sample-count-hint" className="text-sm text-ink-muted mt-3">
                  기본: 5개, 최대: 20개 (더 많은 샘플일수록 정확도가 높아집니다)
                </p>
              </div>

              <div className="p-6 bg-accent/20 border border-accent/30 rounded-2xl">
                <h3 className="font-semibold text-ink mb-4">분석 항목</h3>
                <ul className="text-sm text-ink space-y-2">
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
                className="w-full px-8 py-5 bg-accent text-ink rounded-full motion-safe:hover:scale-105 transition-transform font-semibold text-lg disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {loading ? '분석 중...' : '분석 시작'}
              </button>

              {result && (
                <div className="p-8 bg-accent/20 border border-accent/30 rounded-2xl">
                  <div className="flex items-start gap-6">
                    <div className="flex-shrink-0">
                      <svg className="w-10 h-10 text-accent-ink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <h3 className="font-bold text-ink mb-3 text-xl">
                        {result.status === 'succeeded'
                          ? 'Style DNA가 완성되었습니다!'
                          : result.status === 'failed'
                            ? '분석에 실패했습니다'
                            : 'Style DNA를 분석하고 있습니다'}
                      </h3>
                      <p className="text-ink mb-6">
                        {result.status === 'succeeded'
                          ? '이제 새 글을 만들 때 이 스타일을 선택할 수 있습니다.'
                          : result.status === 'failed'
                            ? result.error_text || '블로그 주소를 다시 확인해주세요.'
                            : '보통 1~2분 정도 걸립니다. 이 페이지를 열어두면 자동으로 갱신됩니다.'}
                      </p>
                      <div className="space-y-2 text-sm text-ink mb-6">
                        <p><strong>상태:</strong> {statusLabel[result.status]}</p>
                        <p><strong>Profile ID:</strong> {result.id}</p>
                      </div>
                      <Link
                        href="/dashboard"
                        className="inline-block px-6 py-3 bg-ink text-canvas rounded-full motion-safe:hover:scale-105 transition-transform font-semibold"
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
