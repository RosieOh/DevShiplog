import Link from 'next/link'
import { FreshnessDot } from '@/components/blog/FreshnessBadge'
import { formatDate } from '@/lib/api/public'
import type { PostCard, StackSummary } from '@/lib/api/public'

/**
 * 처음 온 사람이 보는 화면.
 *
 * 설명으로 시작하지 않는다. "낡은 글" 문제는 겪어 본 사람에게는 설명이 필요 없고,
 * 안 겪어 본 사람에게는 설명해도 와닿지 않는다. 대신 **자기 스택**을 고르게 한다 —
 * 방문자가 자기 상황으로 들어오는 순간 이 제품이 무엇인지 한 번에 이해된다.
 *
 * 아래에 실제 글을 신선도와 함께 놓는다. 여기서 문장이 하는 일은 거의 없고,
 * "8개월 전 확인 · React 17 기준" 이라는 실물이 대신 말한다.
 */
export default function Landing({
  stacks,
  posts,
}: {
  stacks: StackSummary[]
  posts: PostCard[]
}) {
  return (
    <div className="mx-auto w-full max-w-shell px-4 md:px-6">
      <div className="mx-auto w-full max-w-content lg:mx-0">
        <section className="pb-14 pt-16 sm:pb-20 sm:pt-24">
          <h1 className="text-[2.25rem] font-extrabold leading-[1.2] tracking-tight text-ink text-balance sm:text-[3rem]">
            발행하고 끝나지 않는
            <br />
            기술 블로그
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-muted">
            글은 시간이 지나면 틀린 글이 됩니다. 여기서는 글을{' '}
            <b className="font-bold text-ink">어떤 스택의 어떤 버전에서, 언제 확인된 절차</b>로
            다룹니다.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Link
              href="/auth/login?mode=signup"
              className="inline-flex min-h-touch items-center rounded bg-ink px-6 font-bold text-bg transition-opacity hover:opacity-85"
            >
              글 쓰러 가기
            </Link>
            <Link
              href="/about"
              className="inline-flex min-h-touch items-center rounded px-4 font-medium text-ink-muted transition-colors hover:text-ink"
            >
              어떻게 동작하나요
            </Link>
          </div>
        </section>

        {/*
          * 스택 색인. 방문자가 자기 상황으로 들어오는 문이다.
          * 글 수를 같이 적는 이유: 빈 곳을 눌러 빈 화면을 만나면 신뢰를 잃는다.
          */}
        {stacks.length > 0 && (
          <section className="border-t border-border py-12">
            <h2 className="text-xl font-bold tracking-tight text-ink">무슨 스택을 쓰세요?</h2>
            <p className="mt-2 text-ink-muted">
              고르면 그 스택 글이 <b className="font-medium text-ink">언제 확인됐는지</b>와 함께
              나옵니다.
            </p>

            <ul className="mt-6 flex flex-wrap gap-2">
              {stacks.map((stack) => (
                <li key={stack.name}>
                  <Link
                    href={`/stacks/${encodeURIComponent(stack.name)}`}
                    className="inline-flex min-h-touch items-baseline gap-2 rounded border border-border px-4 transition-colors hover:border-ink hover:bg-surface-2"
                  >
                    <span className="font-medium text-ink">{stack.name}</span>
                    <span className="font-mono text-xs tabular-nums text-ink-faint">
                      {stack.post_count}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/*
          * 증거. 말로 "낡음을 관리합니다" 라고 하는 대신 실제 글을 그대로 보여준다.
          * 상태가 섞여 있는 편이 낫다 — 전부 초록이면 광고처럼 보이고,
          * 실제로도 대부분의 글은 아직 검증되지 않았다.
          */}
        {posts.length > 0 && (
          <section className="border-t border-border py-12">
            <h2 className="text-xl font-bold tracking-tight text-ink">지금 올라온 글</h2>
            <ul className="mt-6 divide-y divide-border-subtle">
              {posts.map((post) => (
                <li key={post.id} className="py-5 first:pt-0">
                  <Link href={post.url} className="group block">
                    <h3 className="font-bold leading-snug text-ink underline-offset-4 group-hover:underline">
                      {post.title}
                    </h3>
                    <div className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-sm text-ink-faint">
                      <FreshnessDot freshness={post.freshness} />
                      {post.stacks.length > 0 && (
                        <>
                          <span aria-hidden="true">·</span>
                          <span className="font-mono text-xs tabular-nums">
                            {post.stacks
                              .slice(0, 3)
                              .map((s) => (s.version ? `${s.name} ${s.version}` : s.name))
                              .join('  ·  ')}
                          </span>
                        </>
                      )}
                      <span aria-hidden="true">·</span>
                      <time dateTime={post.published_at ?? undefined}>
                        {formatDate(post.published_at)}
                      </time>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>

            <Link
              href="/?sort=recent"
              className="mt-6 inline-flex min-h-touch items-center text-sm font-medium text-accent-text underline-offset-4 hover:underline"
            >
              전체 글 보기 →
            </Link>
          </section>
        )}
      </div>
    </div>
  )
}
