import Link from 'next/link'
import Avatar from '@/components/ui/Avatar'
import { FreshnessDot } from '@/components/blog/FreshnessBadge'
import type { PostCard as PostCardData } from '@/lib/api/public'
import { formatDate } from '@/lib/api/public'

/**
 * 피드 한 줄.
 *
 * 카드 그리드에서 리스트로 바꾼 이유: 카드는 항목을 **같은 크기의 상자**로 만든다.
 * 상자가 격자로 늘어서면 무엇을 먼저 읽을지가 사라지고 화면이 관리도구처럼 보인다.
 * 읽을거리를 고르는 화면에서 필요한 것은 상자가 아니라 **제목의 위계**다.
 *
 * 그래서 제목을 크게 두고, 나머지는 제목 아래 한 줄로 눕힌다.
 * 훑을 때 눈이 제목만 따라 내려가고, 멈춘 곳에서만 아래 줄을 읽게 된다.
 */
export default function PostRow({ post }: { post: PostCardData }) {
  return (
    <article className="group relative py-8 first:pt-0">
      <div className="flex gap-6 sm:gap-8">
        <div className="min-w-0 flex-1">
          <h2 className="text-xl font-bold leading-snug tracking-tight text-ink text-balance sm:text-[1.6rem]">
            <Link href={post.url} className="after:absolute after:inset-0">
              {post.title}
            </Link>
          </h2>

          {post.summary && (
            <p className="mt-2.5 line-clamp-2 leading-relaxed text-ink-muted">{post.summary}</p>
          )}

          {/*
            * 스택은 배지 대신 한 줄로 눕힌다. 목록에서는 "무엇을 쓰는 글인가" 만
            * 알면 되고, 배지가 여러 개 뜨면 제목보다 눈에 먼저 들어온다.
            */}
          {post.stacks.length > 0 && (
            <p className="mt-3 truncate font-mono text-xs tabular-nums text-ink-faint">
              {post.stacks
                .slice(0, 4)
                .map((s) => (s.version ? `${s.name} ${s.version}` : s.name))
                .join('  ·  ')}
            </p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-sm text-ink-faint">
            <span className="inline-flex items-center gap-1.5">
              <Avatar
                handle={post.author.handle}
                displayName={post.author.display_name}
                src={post.author.avatar_url}
                size={20}
              />
              <span className="font-medium text-ink-muted">{post.author.display_name}</span>
            </span>
            <span aria-hidden="true">·</span>
            <time dateTime={post.published_at ?? undefined}>{formatDate(post.published_at)}</time>
            {post.comment_count > 0 && (
              <>
                <span aria-hidden="true">·</span>
                <span>댓글 {post.comment_count}</span>
              </>
            )}
            {post.like_count > 0 && (
              <>
                <span aria-hidden="true">·</span>
                <span>좋아요 {post.like_count}</span>
              </>
            )}
            {/* 클릭한 뒤에야 낡은 글인 걸 알면 독자의 시간을 이미 쓴 뒤다. */}
            <span aria-hidden="true">·</span>
            <FreshnessDot freshness={post.freshness} />
          </div>
        </div>

        {/*
          * 썸네일은 있는 글에만. 없는 글에 회색 사각형이나 자동 그라디언트를 넣으면
          * "내용 없음" 을 장식으로 덮는 꼴이 되고, 목록의 리듬도 그쪽에 끌려간다.
          */}
        {post.cover_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={post.cover_url}
            alt=""
            loading="lazy"
            className="hidden h-24 w-32 shrink-0 rounded object-cover sm:block sm:h-28 sm:w-44"
          />
        )}
      </div>
    </article>
  )
}
