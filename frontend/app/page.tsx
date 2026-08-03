import type { Metadata } from 'next'
import Link from 'next/link'
import PostCard from '@/components/blog/PostCard'
import { getFeed, getPopularTags, SITE_NAME, SITE_URL } from '@/lib/api/public'

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

export default async function HomePage({
  searchParams,
}: {
  searchParams: { sort?: string }
}) {
  const sort = searchParams.sort === 'trending' ? 'trending' : 'recent'
  const [feed, tags] = await Promise.all([getFeed({ sort }), getPopularTags(12)])
  const posts = feed?.items ?? []

  return (
    <div className="bg-canvas min-h-screen">
      <div className="mx-auto max-w-[1100px] px-[5%] py-12">
        <div className="grid gap-12 lg:grid-cols-[1fr_260px]">
          <main>
            <div className="mb-8 flex items-center gap-1 border-b border-black/10 pb-4">
              {(
                [
                  { key: 'recent', label: '최신' },
                  { key: 'trending', label: '인기' },
                ] as const
              ).map((t) => (
                <Link
                  key={t.key}
                  href={t.key === 'recent' ? '/' : '/?sort=trending'}
                  aria-current={sort === t.key ? 'page' : undefined}
                  className={`inline-flex min-h-touch items-center rounded-full px-4 text-sm font-semibold transition-colors ${
                    sort === t.key ? 'bg-accent text-ink' : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  {t.label}
                </Link>
              ))}
            </div>

            {posts.length === 0 ? (
              <div className="rounded-[32px] border border-black/5 bg-surface p-12 text-center">
                <h1 className="text-2xl font-bold text-ink">아직 발행된 글이 없습니다</h1>
                <p className="mt-3 text-ink-muted">첫 글을 써서 이 자리를 채워보세요.</p>
                <Link
                  href="/drafts/new"
                  className="mt-6 inline-flex min-h-touch items-center rounded-full bg-accent px-8 font-semibold text-ink motion-safe:hover:scale-105 transition-transform"
                >
                  글 쓰러 가기
                </Link>
              </div>
            ) : (
              <>
                <h1 className="sr-only">{sort === 'trending' ? '인기 글' : '최신 글'}</h1>
                {posts.map((post) => (
                  <PostCard key={post.id} post={post} />
                ))}
              </>
            )}
          </main>

          <aside className="lg:pt-4">
            <h2 className="text-sm font-bold uppercase tracking-wider text-ink-muted">태그</h2>
            {tags && tags.length > 0 ? (
              <ul className="mt-4 flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <li key={tag.name}>
                    <Link
                      href={`/tags/${encodeURIComponent(tag.name)}`}
                      className="inline-flex items-center rounded-full border border-black/10 bg-surface px-3 py-1.5 text-sm text-ink-muted transition-colors hover:border-black/20 hover:text-ink"
                    >
                      {tag.display_name}
                      <span className="ml-1.5 text-xs text-ink-muted/70">{tag.post_count}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-ink-muted">아직 태그가 없습니다.</p>
            )}
          </aside>
        </div>
      </div>
    </div>
  )
}
