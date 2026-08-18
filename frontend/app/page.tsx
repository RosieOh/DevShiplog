import type { Metadata } from 'next'
import Link from 'next/link'
import PostRow from '@/components/blog/PostRow'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import Landing from '@/components/landing/Landing'
import { getFeed, getPopularStacks, SITE_NAME, SITE_URL } from '@/lib/api/public'

/**
 * 홈. 보는 사람에 따라 다른 화면을 준다.
 *
 * - 로그인 안 함 → 랜딩. 처음 온 사람에게 모르는 사람 글 20개를 보여주면
 *   이게 뭐 하는 곳인지, 왜 여기 써야 하는지를 알 방법이 없다.
 * - 로그인함 → 피드. 돌아온 사람에게 소개를 다시 읽히면 클릭만 늘어난다.
 *
 * 예전 주석은 "`/` 에 콘텐츠가 있어야 크롤러가 글까지 간다" 였는데, 이 프로젝트에는
 * sitemap.ts 와 robots.ts 가 있고 백엔드가 전체 글 목록을 낸다. 크롤러는 `/` 를
 * 거치지 않고 사이트맵으로 글에 바로 간다.
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

  const session = await getServerSession(authOptions)

  // 처음 온 사람에게는 랜딩. 검색 크롤러도 여기를 보지만, 글은 사이트맵으로 간다.
  if (!session) {
    const [stacks, recent] = await Promise.all([
      getPopularStacks(12),
      getFeed({ sort: 'recent', limit: 5 }),
    ])
    return <Landing stacks={stacks ?? []} posts={recent?.items ?? []} />
  }

  const feed = await getFeed({ sort, period, limit: 24 })
  const posts = feed?.items ?? []

  const emptyMessage: Record<Sort, string> = {
    trending: '이 기간에 반응을 받은 글이 아직 없습니다.',
    recommended: '추천할 글이 아직 없습니다. 마음에 드는 글에 좋아요를 눌러보세요.',
    recent: '아직 발행된 글이 없습니다.',
    following: '팔로우한 사람의 글이 아직 없습니다.',
  }

  return (
    <div className="mx-auto w-full max-w-shell px-4 py-6 md:px-6">
      <div className="mx-auto w-full max-w-content lg:mx-0">
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
          {/*
            * 항목 사이는 선 하나로만 나눈다. 카드로 감싸면 목록이 상자의 나열이 되고,
            * 상자가 같은 크기로 늘어서는 순간 무엇을 먼저 읽을지가 사라진다.
            */}
          <div className="divide-y divide-border-subtle">
            {posts.map((post) => (
              <PostRow key={post.id} post={post} />
            ))}
          </div>
        </>
      )}
    </div>
    </div>
  )
}
