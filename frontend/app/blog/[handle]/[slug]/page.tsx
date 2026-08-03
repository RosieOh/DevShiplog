import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import Markdown from '@/components/blog/Markdown'
import PostActions from '@/components/blog/PostActions'
import CommentSection from '@/components/blog/CommentSection'
import { formatDate, getPost, SITE_NAME, SITE_URL } from '@/lib/api/public'

interface Props {
  params: { handle: string; slug: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const handle = decodeURIComponent(params.handle)
  const slug = decodeURIComponent(params.slug)
  const post = await getPost(handle, slug)
  if (!post) return { title: '글을 찾을 수 없습니다' }

  const url = `${SITE_URL}${post.url}`
  const description = post.summary ?? undefined

  return {
    title: post.title,
    description,
    // 태그 페이지·피드에도 같은 글이 나오므로 정본 주소를 못 박는다.
    alternates: { canonical: url },
    authors: [{ name: post.author.display_name, url: `${SITE_URL}/@${post.author.handle}` }],
    keywords: post.tags,
    openGraph: {
      type: 'article',
      url,
      siteName: SITE_NAME,
      title: post.title,
      description,
      publishedTime: post.published_at ?? undefined,
      authors: [post.author.display_name],
      tags: post.tags,
      ...(post.cover_url ? { images: [{ url: post.cover_url }] } : {}),
    },
    twitter: {
      card: post.cover_url ? 'summary_large_image' : 'summary',
      title: post.title,
      description,
      ...(post.cover_url ? { images: [post.cover_url] } : {}),
    },
  }
}

export default async function PostPage({ params }: Props) {
  const handle = decodeURIComponent(params.handle)
  const slug = decodeURIComponent(params.slug)
  const post = await getPost(handle, slug)

  if (!post) notFound()

  // 검색결과에 저자·발행일이 함께 노출되도록 구조화 데이터를 심는다.
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.title,
    description: post.summary,
    datePublished: post.published_at,
    author: {
      '@type': 'Person',
      name: post.author.display_name,
      url: `${SITE_URL}/@${post.author.handle}`,
    },
    publisher: { '@type': 'Organization', name: SITE_NAME },
    mainEntityOfPage: `${SITE_URL}${post.url}`,
    ...(post.cover_url ? { image: post.cover_url } : {}),
  }

  return (
    <div className="bg-canvas min-h-screen">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <article className="mx-auto max-w-[760px] px-[5%] py-12">
        <header className="border-b border-black/10 pb-8">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-ink text-balance">
            {post.title}
          </h1>

          <div className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
            <Link
              href={`/@${post.author.handle}`}
              className="font-semibold text-ink hover:underline underline-offset-2"
            >
              {post.author.display_name}
            </Link>
            <span aria-hidden="true">·</span>
            <time dateTime={post.published_at ?? undefined}>{formatDate(post.published_at)}</time>
            <span aria-hidden="true">·</span>
            <span>조회 {post.view_count}</span>
          </div>

          {post.tags.length > 0 && (
            <ul className="mt-5 flex flex-wrap gap-2">
              {post.tags.map((tag) => (
                <li key={tag}>
                  <Link
                    href={`/tags/${encodeURIComponent(tag.toLowerCase())}`}
                    className="inline-flex items-center rounded-full bg-surface border border-black/10 px-3 py-1 text-xs font-medium text-ink-muted transition-colors hover:text-ink"
                  >
                    {tag}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </header>

        <div className="py-10">
          <Markdown>{post.content_md}</Markdown>
        </div>

        <PostActions
          postId={post.id}
          initialLiked={post.is_liked}
          initialLikeCount={post.like_count}
          authorHandle={post.author.handle}
          isMine={post.is_mine}
        />

        <CommentSection
          postId={post.id}
          handle={handle}
          slug={slug}
          comments={post.comments}
          commentCount={post.comment_count}
        />
      </article>
    </div>
  )
}
