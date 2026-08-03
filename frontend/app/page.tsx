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

const TABS = [
  { key: 'trending', label: '트렌딩', href: '/?sort=trending' },
  { key: 'recent', label: '최신', href: '/' },
] as const

function TrendIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m3 17 6-6 4 4 8-8" />
      <path d="M15 7h6v6" />
    </svg>
  )
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: { sort?: string }
}) {
  const sort = searchParams.sort === 'trending' ? 'trending' : 'recent'
  const feed = await getFeed({ sort, limit: 24 })
  const posts = feed?.items ?? []

  return (
    <div className="mx-auto max-w-shell px-4 py-6 md:px-6">
      <nav aria-label="정렬" className="mb-6 flex items-center gap-6 border-b border-border">
        {TABS.map((tab) => {
          const active = sort === tab.key
          const Icon = tab.key === 'trending' ? TrendIcon : ClockIcon
          return (
            <Link
              key={tab.key}
              href={tab.href}
              aria-current={active ? 'page' : undefined}
              className={`-mb-px flex items-center gap-1.5 border-b-2 pb-3 pt-1 text-lg transition-colors ${
                active
                  ? 'border-ink font-bold text-ink'
                  : 'border-transparent font-medium text-ink-faint hover:text-ink'
              }`}
            >
              <Icon className="h-5 w-5" />
              {tab.label}
            </Link>
          )
        })}
      </nav>

      {posts.length === 0 ? (
        <div className="rounded bg-surface px-6 py-20 text-center shadow-card">
          <h1 className="text-xl font-bold text-ink">아직 발행된 글이 없습니다</h1>
          <p className="mt-2 text-sm text-ink-muted">첫 글을 써서 이 자리를 채워보세요.</p>
          <Link
            href="/drafts/new"
            className="mt-6 inline-flex min-h-touch items-center rounded bg-ink px-6 text-sm font-bold text-bg transition-opacity hover:opacity-85"
          >
            글 쓰러 가기
          </Link>
        </div>
      ) : (
        <>
          <h1 className="sr-only">{sort === 'trending' ? '인기 글' : '최신 글'}</h1>
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
