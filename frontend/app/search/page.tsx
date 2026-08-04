import type { Metadata } from 'next'
import PostCard from '@/components/blog/PostCard'
import { searchPosts } from '@/lib/api/public'

export const metadata: Metadata = {
  title: '검색',
  // 검색 결과 페이지는 색인 대상이 아니다. 무한한 조합이 중복 콘텐츠를 만든다.
  robots: { index: false, follow: true },
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: { q?: string }
}) {
  const query = (searchParams.q ?? '').trim()
  const result = query ? await searchPosts(query) : null
  const posts = result?.items ?? []

  return (
    <div className="bg-bg min-h-screen">
      <div className="mx-auto max-w-[820px] px-[5%] py-12">
        <form action="/search" method="get" className="border-b border-border pb-8">
          <label htmlFor="q" className="block text-sm font-semibold text-ink">
            검색
          </label>
          <div className="mt-3 flex gap-2">
            <input
              id="q"
              name="q"
              type="search"
              defaultValue={query}
              placeholder="제목이나 요약으로 검색"
              className="flex-1 rounded border border-border bg-surface p-4"
            />
            <button
              type="submit"
              className="inline-flex min-h-touch items-center rounded bg-ink px-6 font-semibold text-bg"
            >
              검색
            </button>
          </div>
        </form>

        <main>
          {!query ? (
            <p className="py-16 text-center text-ink-muted">검색어를 입력해주세요.</p>
          ) : posts.length > 0 ? (
            <>
              <h1 className="py-6 text-sm text-ink-muted">
                “{query}” 검색 결과 {posts.length}건
              </h1>
              {posts.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </>
          ) : (
            <p className="py-16 text-center text-ink-muted">
              “{query}”와 일치하는 글이 없습니다.
            </p>
          )}
        </main>
      </div>
    </div>
  )
}
