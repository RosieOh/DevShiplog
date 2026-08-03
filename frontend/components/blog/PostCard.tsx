import Link from 'next/link'
import type { PostCard as PostCardData } from '@/lib/api/public'
import { formatDate } from '@/lib/api/public'

export default function PostCard({ post }: { post: PostCardData }) {
  return (
    <article className="border-b border-black/10 py-8 last:border-0">
      <Link href={post.url} className="group block">
        <h2 className="text-2xl font-bold text-ink tracking-tight group-hover:underline underline-offset-4 text-balance">
          {post.title}
        </h2>
        {post.summary && (
          <p className="mt-3 text-ink-muted leading-relaxed line-clamp-2">{post.summary}</p>
        )}
      </Link>

      {post.tags.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2">
          {post.tags.map((tag) => (
            <li key={tag}>
              <Link
                href={`/tags/${encodeURIComponent(tag.toLowerCase())}`}
                className="inline-flex items-center rounded-full bg-canvas border border-black/10 px-3 py-1 text-xs font-medium text-ink-muted hover:text-ink hover:border-black/20 transition-colors"
              >
                {tag}
              </Link>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
        <Link
          href={`/@${post.author.handle}`}
          className="font-medium text-ink hover:underline underline-offset-2"
        >
          {post.author.display_name}
        </Link>
        <span aria-hidden="true">·</span>
        <time dateTime={post.published_at ?? undefined}>{formatDate(post.published_at)}</time>
        <span aria-hidden="true">·</span>
        <span>좋아요 {post.like_count}</span>
        <span aria-hidden="true">·</span>
        <span>댓글 {post.comment_count}</span>
      </div>
    </article>
  )
}
