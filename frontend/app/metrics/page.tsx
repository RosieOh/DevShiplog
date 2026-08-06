'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { apiClient } from '@/lib/api/client'

interface Summary {
  stack_correction: {
    publishes: number
    corrected: number
    rate: number | null
    published_empty: number
  }
  reverification: { verified_posts: number; reverified_posts: number; rate: number | null }
  signal_response: {
    signaled_posts: number
    responded: number
    rate: number | null
    median_hours: number | null
  }
  verdicts: string[]
}

/**
 * 신선도 기능이 실제로 값어치가 있는가.
 *
 * "쓸 만해 보인다" 는 판단 근거가 아니다. 접을지 말지를 정하려면 수가 있어야 하고,
 * 그 수를 볼 곳이 없으면 아무도 안 본다.
 *
 * 지표를 잘 보이게 만드는 것 자체가 "안 되면 접는다" 는 약속을 지키는 방법이다.
 */

function Metric({
  label,
  value,
  detail,
  question,
}: {
  label: string
  value: string
  detail: string
  question: string
}) {
  return (
    <div className="rounded border border-border bg-surface p-5">
      <p className="text-xs font-bold uppercase tracking-wider text-ink-faint">{label}</p>
      <p className="mt-3 font-mono text-3xl font-bold tabular-nums text-ink">{value}</p>
      <p className="mt-1 font-mono text-xs tabular-nums text-ink-faint">{detail}</p>
      <p className="mt-4 border-t border-border-subtle pt-3 text-sm leading-relaxed text-ink-muted">
        {question}
      </p>
    </div>
  )
}

export default function MetricsPage() {
  const { status } = useSession()
  const router = useRouter()
  const [data, setData] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (status === 'loading') return
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }
    apiClient
      .get<Summary>('/api/v1/posts/metrics/product')
      .then(setData)
      .catch(() => undefined)
      .finally(() => setLoading(false))
  }, [status, router])

  if (loading) {
    return (
      <div className="mx-auto max-w-shell px-4 py-12 md:px-6">
        <p className="text-ink-muted">불러오는 중...</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-shell px-4 py-12 md:px-6">
        <p className="text-ink-muted">지표를 불러오지 못했습니다.</p>
      </div>
    )
  }

  const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v * 100)}%`)
  const { stack_correction: sc, reverification: rv, signal_response: sr } = data

  return (
    <div className="mx-auto max-w-shell px-4 py-8 md:px-6">
      <header className="border-b border-border pb-6">
        <p className="font-mono text-xs uppercase tracking-widest text-ink-faint">제품 지표</p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-ink">
          신선도가 실제로 값어치가 있는가
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-muted">
          아래 셋이 안 돌면 신선도는 우리만 좋아하는 기능입니다. 그때는 접습니다.
          숫자를 보이게 두는 것 자체가 그 약속을 지키는 방법입니다.
        </p>
      </header>

      {/* 판정을 위에 둔다. 숫자만 보면 "나쁘지 않네" 로 넘어간다. */}
      <ul className="mt-6 space-y-2">
        {data.verdicts.map((verdict) => {
          const neutral = verdict.includes('표본') || verdict.includes('넘습니다')
          return (
            <li
              key={verdict}
              className={`rounded border px-4 py-3 text-sm ${
                neutral
                  ? 'border-border bg-surface-2 text-ink-muted'
                  : 'border-stale/40 bg-stale/8 font-medium text-stale'
              }`}
            >
              {verdict}
            </li>
          )
        })}
      </ul>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Metric
          label="1 · 추출 품질"
          value={pct(sc.rate)}
          detail={`발행 ${sc.publishes} · 보정 ${sc.corrected} · 스택 없이 ${sc.published_empty}`}
          question="자동 추출이 쓸 만한가. 0% 면 추출이 완벽하거나 아무도 확인하지 않은 것이고, 둘은 전혀 다른 상황이다. 20~50% 를 기대한다."
        />
        <Metric
          label="2 · 재검증"
          value={pct(rv.rate)}
          detail={`검증된 글 ${rv.verified_posts} · 두 번 이상 ${rv.reverified_posts}`}
          question="갱신 루프가 도는가. 두 번째 검증부터가 진짜다 — 첫 번째는 발행 직후의 의욕이고, 두 번째는 이 제품이 나를 다시 데려왔는가다."
        />
        <Metric
          label="3 · 신호 반응"
          value={pct(sr.rate)}
          detail={`신고받은 글 ${sr.signaled_posts} · 반응 ${sr.responded}${
            sr.median_hours !== null ? ` · 중앙값 ${sr.median_hours}시간` : ''
          }`}
          question="독자 신호가 작성자를 움직이는가. 안 돌면 신호는 작성자에게 잔소리일 뿐이다."
        />
      </div>

      <p className="mt-6 text-xs leading-relaxed text-ink-faint">
        집계값만 표시합니다. 개인을 식별하는 정보는 기록하지 않습니다.
      </p>
    </div>
  )
}
