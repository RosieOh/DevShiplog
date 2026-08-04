import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import Avatar from '@/components/ui/Avatar'
import PostCard from '@/components/blog/PostCard'
import FollowButton from '@/components/blog/FollowButton'
import { getBlog, getBlogPosts, SITE_NAME, SITE_URL } from '@/lib/api/public'

interface Props {
  params: { handle: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const handle = decodeURIComponent(params.handle)
  const blog = await getBlog(handle)
  if (!blog) return { title: '블로그를 찾을 수 없습니다' }

  const title = `${blog.display_name} (@${blog.handle})`
  const description = blog.bio || `${blog.display_name}님의 기술 블로그`
  const url = `${SITE_URL}/@${blog.handle}`

  return {
    title,
    description,
    alternates: {
      canonical: url,
      // 남의 RSS 를 읽던 입장에서 이제 내보내는 쪽이 된다.
      types: { 'application/rss+xml': `${url}/rss.xml` },
    },
    openGraph: { type: 'profile', url, siteName: SITE_NAME, title, description },
    twitter: { card: 'summary', title, description },
  }
}

export default async function BlogHomePage({ params }: Props) {
  const handle = decodeURIComponent(params.handle)
  const [blog, posts] = await Promise.all([getBlog(handle), getBlogPosts(handle, 24)])

  if (!blog) notFound()

  return (
    <div className="mx-auto max-w-shell px-4 py-12 md:px-6">
      <header className="border-b border-border pb-10">
        <div className="flex flex-wrap items-start gap-6">
          <Avatar
            handle={blog.handle}
            displayName={blog.display_name}
            src={blog.avatar_url}
            size={128}
            className="shadow-card"
          />
          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-extrabold tracking-tight text-ink">
              {blog.display_name}
            </h1>
            <p className="mt-1 text-ink-faint">@{blog.handle}</p>
            {blog.bio && (
              <p className="mt-4 max-w-prose leading-relaxed text-ink-muted">{blog.bio}</p>
            )}
            <dl className="mt-5 flex flex-wrap gap-6 text-sm text-ink-muted">
              <div className="flex gap-1.5">
                <dt>글</dt>
                <dd className="font-bold text-ink">{blog.post_count}</dd>
              </div>
              <div className="flex gap-1.5">
                <dt>팔로워</dt>
                <dd className="font-bold text-ink">{blog.follower_count}</dd>
              </div>
              <div className="flex gap-1.5">
                <dt>팔로잉</dt>
                <dd className="font-bold text-ink">{blog.following_count}</dd>
              </div>
            </dl>
          </div>
          <FollowButton handle={blog.handle} />
        </div>

        {blog.series.length > 0 && (
          <nav aria-label="시리즈" className="mt-8">
            <h2 className="text-xs font-bold uppercase tracking-wider text-ink-faint">시리즈</h2>
            <ul className="mt-3 flex flex-wrap gap-2">
              {blog.series.map((s) => (
                <li key={s.slug}>
                  <Link
                    href={`/@${blog.handle}/series/${encodeURIComponent(s.slug)}`}
                    className="inline-flex items-center rounded border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors hover:border-ink-faint"
                  >
                    {s.name}
                    <span className="ml-2 text-xs text-ink-faint">{s.post_count}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        )}
      </header>

      <main className="pt-8">
        {posts && posts.items.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {posts.items.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        ) : (
          <p className="py-20 text-center text-ink-muted">아직 발행한 글이 없습니다.</p>
        )}
      </main>
    </div>
  )
}
