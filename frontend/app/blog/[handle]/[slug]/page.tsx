import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import Avatar from '@/components/ui/Avatar'
import Markdown from '@/components/blog/Markdown'
import PostActions from '@/components/blog/PostActions'
import CommentSection from '@/components/blog/CommentSection'
import TableOfContents from '@/components/blog/TableOfContents'
import FloatingActions from '@/components/blog/FloatingActions'
import { extractToc } from '@/lib/toc'
import { absoluteUrl, formatDate, getPost, SITE_NAME, SITE_URL } from '@/lib/api/public'

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

  // 목차는 서버에서 뽑는다. 클라이언트에서 DOM 을 훑으면 첫 페인트에 비어 있고
  // 크롤러도 읽지 못한다.
  const toc = extractToc(post.content_md)

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
    // JSON-LD 는 metadataBase 같은 자동 보정이 없다. 크롤러가 쓰려면 절대 주소여야 한다.
    ...(post.cover_url ? { image: absoluteUrl(post.cover_url) } : {}),
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <FloatingActions
        postId={post.id}
        initialLiked={post.is_liked}
        initialLikeCount={post.like_count}
      />

      <div className="mx-auto grid max-w-shell grid-cols-1 gap-10 px-4 py-12 md:px-6 lg:grid-cols-[minmax(0,1fr)_220px]">
      <article className="mx-auto w-full max-w-content lg:mx-0">
        <header>
          <h1 className="text-[2rem] font-extrabold leading-[1.3] tracking-tight text-ink text-balance md:text-[2.5rem]">
            {post.title}
          </h1>

          <div className="mt-6 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink-muted">
            <Link
              href={`/@${post.author.handle}`}
              className="font-bold text-ink hover:underline underline-offset-2"
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
                    className="inline-flex items-center rounded-full bg-accent/12 px-3.5 py-1.5 text-sm font-medium text-accent-text transition-colors hover:bg-accent/20"
                  >
                    {tag}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </header>

        {post.cover_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={post.cover_url}
            alt=""
            className="mt-10 w-full rounded object-cover"
          />
        )}

        <div className="py-12">
          <Markdown>{post.content_md}</Markdown>
        </div>

        <PostActions
          postId={post.id}
          initialLiked={post.is_liked}
          initialLikeCount={post.like_count}
          authorHandle={post.author.handle}
          isMine={post.is_mine}
        />

        {/* 글 끝에서 작성자를 다시 보여준다 — 읽고 나서야 "누가 썼지" 가 궁금해진다. */}
        <aside className="mt-12 flex items-start gap-4 border-t border-border pt-10">
          <Link href={`/@${post.author.handle}`} aria-hidden="true" tabIndex={-1}>
            <Avatar
              handle={post.author.handle}
              displayName={post.author.display_name}
              src={post.author.avatar_url}
              size={64}
            />
          </Link>
          <div className="min-w-0">
            <Link
              href={`/@${post.author.handle}`}
              className="text-xl font-bold text-ink hover:underline underline-offset-2"
            >
              {post.author.display_name}
            </Link>
            <p className="text-sm text-ink-faint">@{post.author.handle}</p>
            {post.author.bio && (
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{post.author.bio}</p>
            )}
          </div>
        </aside>

        <CommentSection
          postId={post.id}
          handle={handle}
          slug={slug}
          comments={post.comments}
          commentCount={post.comment_count}
        />
      </article>

      {toc.length >= 2 && (
        <aside className="hidden lg:block">
          <TableOfContents items={toc} />
        </aside>
      )}
      </div>
    </>
  )
}
