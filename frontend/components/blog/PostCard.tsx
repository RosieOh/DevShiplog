import Link from 'next/link'
import Avatar from '@/components/ui/Avatar'
import type { PostCard as PostCardData } from '@/lib/api/public'
import { formatDate } from '@/lib/api/public'

/**
 * 피드 카드.
 *
 * 썸네일이 없는 글은 이미지 영역을 아예 만들지 않는다. 빈 회색 사각형이나
 * 자동 생성 그라디언트로 채우면 "내용 없음" 을 장식으로 덮는 꼴이 된다.
 */
export default function PostCard({ post }: { post: PostCardData }) {
  return (
    <article className="group flex flex-col overflow-hidden rounded bg-surface shadow-card transition-shadow duration-200 hover:shadow-card-hover">
      {post.cover_url && (
        <Link href={post.url} tabIndex={-1} aria-hidden="true" className="block">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={post.cover_url}
            alt=""
            loading="lazy"
            className="aspect-[16/9] w-full object-cover"
          />
        </Link>
      )}

      <div className="flex flex-1 flex-col p-4">
        <Link href={post.url} className="block">
          <h2 className="line-clamp-2 text-base font-bold leading-snug text-ink">{post.title}</h2>
          {post.summary && (
            <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-ink-muted">
              {post.summary}
            </p>
          )}
        </Link>

        {post.tags.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-1.5">
            {post.tags.slice(0, 3).map((tag) => (
              <li key={tag}>
                <Link
                  href={`/tags/${encodeURIComponent(tag.toLowerCase())}`}
                  className="inline-flex min-h-[32px] items-center rounded-full bg-surface-2 px-3 text-xs font-medium text-ink-muted transition-colors hover:text-accent-text"
                >
                  {tag}
                </Link>
              </li>
            ))}
          </ul>
        )}

        <p className="mt-3 flex-1 text-xs text-ink-faint">
          <time dateTime={post.published_at ?? undefined}>{formatDate(post.published_at)}</time>
          {' · '}
          {post.comment_count}개의 댓글
        </p>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-border-subtle px-4 py-3">
        <Link
          href={`/@${post.author.handle}`}
          className="flex min-w-0 items-center gap-2 text-xs text-ink-muted hover:text-ink"
        >
          <Avatar
            handle={post.author.handle}
            displayName={post.author.display_name}
            src={post.author.avatar_url}
            size={24}
          />
          <span className="truncate">
            by <b className="font-bold text-ink">{post.author.display_name}</b>
          </span>
        </Link>

        <span className="flex shrink-0 items-center gap-1 text-xs text-ink-muted">
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 21s-7.5-4.7-9.6-9A5.4 5.4 0 0 1 12 6.2 5.4 5.4 0 0 1 21.6 12c-2.1 4.3-9.6 9-9.6 9Z" />
          </svg>
          {post.like_count}
        </span>
      </div>
    </article>
  )
}
