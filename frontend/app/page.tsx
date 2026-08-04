import type { Metadata } from 'next'
import Link from 'next/link'
import PostCard from '@/components/blog/PostCard'
import { getFeed, SITE_NAME, SITE_URL } from '@/lib/api/public'

/**
 * 홈 = 공개 피드.
 *
 * 마케팅 랜딩이 아니라 글 목록을 루트에 둔다. 블로그 플랫폼에서 `/` 는
 * 검색엔진이 가장 먼저 크롤링하는 페이지이고, 여기에 실제 콘텐츠가 있어야
 * 내부 링크를 타고 글까지 도달한다. 소개 페이지는 /about 으로 옮겼다.
 */
export const metadata: Metadata = {
  title: `${SITE_NAME} — 개발자를 위한 기술 블로그`,
  description: 'AI가 초안을 만들고, 내 톤으로 다듬어, 바로 발행하는 기술 블로그 플랫폼',
  alternates: { canonical: SITE_URL },
  openGraph: {
    type: 'website',
    url: SITE_URL,
    siteName: SITE_NAME,
    title: `${SITE_NAME} — 개발자를 위한 기술 블로그`,
    description: 'AI가 초안을 만들고, 내 톤으로 다듬어, 바로 발행하는 기술 블로그 플랫폼',
  },
}

type Sort = 'trending' | 'recommended' | 'recent' | 'following'
type Period = 'week' | 'month' | 'year' | 'all'

const SORTS: { key: Sort; label: string }[] = [
  { key: 'trending', label: '트렌딩' },
  { key: 'recommended', label: '추천' },
  { key: 'recent', label: '최신' },
  { key: 'following', label: '피드' },
]

const PERIODS: { key: Period; label: string }[] = [
  { key: 'week', label: '이번 주' },
  { key: 'month', label: '이번 달' },
  { key: 'year', label: '올해' },
  { key: 'all', label: '전체' },
]

function Icon({ sort, className }: { sort: Sort; className?: string }) {
  const common = {
    className,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
  }
  if (sort === 'trending')
    return (
      <svg {...common}>
        <path d="m3 17 6-6 4 4 8-8" />
        <path d="M15 7h6v6" />
      </svg>
    )
  if (sort === 'recommended')
    return (
      <svg {...common}>
        <path d="m12 3 2.6 5.7 6.4.7-4.8 4.3 1.4 6.3L12 17l-5.6 3 1.4-6.3L3 9.4l6.4-.7L12 3Z" />
      </svg>
    )
  if (sort === 'recent')
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </svg>
    )
  return (
    <svg {...common}>
      <path d="M4 11a9 9 0 0 1 9 9" />
      <path d="M4 4a16 16 0 0 1 16 16" />
      <circle cx="5" cy="19" r="1.5" fill="currentColor" />
    </svg>
  )
}

function hrefFor(sort: Sort, period: Period): string {
  const params = new URLSearchParams()
  if (sort !== 'recent') params.set('sort', sort)
  if (sort === 'trending' && period !== 'week') params.set('period', period)
  const q = params.toString()
  return q ? `/?${q}` : '/'
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: { sort?: string; period?: string }
}) {
  const sort = (SORTS.find((s) => s.key === searchParams.sort)?.key ?? 'recent') as Sort
  const period = (PERIODS.find((p) => p.key === searchParams.period)?.key ?? 'week') as Period

  const feed = await getFeed({ sort, period, limit: 24 })
  const posts = feed?.items ?? []

  const emptyMessage: Record<Sort, string> = {
    trending: '이 기간에 반응을 받은 글이 아직 없습니다.',
    recommended: '추천할 글이 아직 없습니다. 마음에 드는 글에 좋아요를 눌러보세요.',
    recent: '아직 발행된 글이 없습니다.',
    following: '팔로우한 사람의 글이 아직 없습니다.',
  }

  return (
    <div className="mx-auto max-w-shell px-4 py-6 md:px-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3 border-b border-border">
        <nav aria-label="정렬" className="flex items-center gap-5 sm:gap-6">
          {SORTS.map((tab) => {
            const active = sort === tab.key
            return (
              <Link
                key={tab.key}
                href={hrefFor(tab.key, period)}
                aria-current={active ? 'page' : undefined}
                className={`-mb-px flex min-h-touch items-center gap-1.5 border-b-2 pb-3 pt-1 text-base transition-colors sm:text-lg ${
                  active
                    ? 'border-ink font-bold text-ink'
                    : 'border-transparent font-medium text-ink-faint hover:text-ink'
                }`}
              >
                <Icon sort={tab.key} className="h-5 w-5" />
                {tab.label}
              </Link>
            )
          })}
        </nav>

        {/* 기간 선택은 트렌딩에서만 의미가 있다. */}
        {sort === 'trending' && (
          <div className="mb-2 flex items-center gap-1" role="group" aria-label="기간">
            {PERIODS.map((p) => (
              <Link
                key={p.key}
                href={hrefFor('trending', p.key)}
                aria-current={period === p.key ? 'true' : undefined}
                className={`rounded px-2.5 py-1.5 text-sm transition-colors ${
                  period === p.key
                    ? 'bg-surface-2 font-bold text-ink'
                    : 'text-ink-faint hover:text-ink'
                }`}
              >
                {p.label}
              </Link>
            ))}
          </div>
        )}
      </div>

      {posts.length === 0 ? (
        <div className="rounded bg-surface px-6 py-20 text-center shadow-card">
          <h1 className="text-xl font-bold text-ink">{emptyMessage[sort]}</h1>
          <Link
            href="/drafts/new"
            className="mt-6 inline-flex min-h-touch items-center rounded bg-ink px-6 text-sm font-bold text-bg transition-opacity hover:opacity-85"
          >
            글 쓰러 가기
          </Link>
        </div>
      ) : (
        <>
          <h1 className="sr-only">{SORTS.find((s) => s.key === sort)?.label} 글</h1>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {posts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
