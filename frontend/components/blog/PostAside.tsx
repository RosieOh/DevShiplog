import Link from 'next/link'
import Avatar from '@/components/ui/Avatar'
import TableOfContents from '@/components/blog/TableOfContents'
import { FreshnessDot } from '@/components/blog/FreshnessBadge'
import { formatDate } from '@/lib/api/public'
import type { Freshness, PostStack } from '@/lib/api/public'
import type { TocItem } from '@/lib/toc'

/**
 * 글 옆에 붙는 판단 근거.
 *
 * 예전에는 목차만 있었고, 목차가 없는 글에서는 우측이 통째로 빈 칸이었다
 * (발행 글의 절반 이상이 그랬다). 그렇다고 목차를 억지로 띄우는 건 답이 아니다 —
 * 채워야 할 것은 공간이 아니라 **독자가 읽기 전에 알아야 할 것**이다.
 *
 * 이 제품에서 그건 하나로 정해져 있다. 글은 텍스트 덩어리가 아니라
 * "어떤 스택의 어떤 버전에서, 언제 확인된 절차" 다. 그 세 가지를 본문 옆에 고정한다.
 *
 * 카드를 여러 장 쌓지 않는다. 하나의 세로 레일에 얇은 구분선만 둔다 —
 * 카드가 겹치면 각 조각이 독립된 위젯처럼 보이고, 사실 이것들은 한 문장이다.
 */
export default function PostAside({
  stacks,
  freshness,
  author,
  toc,
}: {
  stacks: PostStack[]
  freshness: Freshness
  author: {
    handle: string
    display_name: string
    avatar_url?: string | null
  }
  toc: TocItem[]
}) {
  const outdated = freshness.outdated ?? []
  const behind = new Set(outdated.map((s) => s.name))

  return (
    // 본문을 따라 내려간다. 판단 근거는 다 읽고 나서가 아니라 읽는 동안 필요하다.
    <div className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto pb-8">
      {stacks.length > 0 && (
        <section>
          <h2 className="text-xs font-bold uppercase tracking-wider text-ink-faint">
            이 글의 전제
          </h2>
          <ul className="mt-3 space-y-px">
            {stacks.map((stack) => (
              <li key={stack.name}>
                <Link
                  href={`/stacks/${encodeURIComponent(stack.name)}${
                    stack.version ? `?version=${encodeURIComponent(stack.version)}` : ''
                  }`}
                  className="-mx-2 flex min-h-touch items-baseline justify-between gap-3 rounded px-2 transition-colors hover:bg-surface-2"
                >
                  <span className="truncate text-sm text-ink">{stack.name}</span>
                  {/*
                    * 등폭은 장식이 아니다. 버전은 숫자고, 세로로 놓일 때
                    * 자릿수가 맞아야 훑어진다.
                    */}
                  <span
                    className={`shrink-0 font-mono text-xs tabular-nums ${
                      behind.has(stack.name) ? 'text-aging' : 'text-ink-faint'
                    }`}
                  >
                    {stack.version ?? '—'}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/*
        * 상태만 둔다. 이유는 본문 위 배너가 이미 한 문장으로 말하고 있고,
        * 넓은 화면에서는 그 배너와 여기가 나란히 놓여 같은 말이 두 번 보인다.
        * 배너는 스크롤하면 사라지지만 이건 남는다 — 그게 여기 있는 이유다.
        */}
      <section className={stacks.length > 0 ? 'mt-6 border-t border-border-subtle pt-6' : ''}>
        <FreshnessDot freshness={freshness} />
        <p className="mt-1.5 font-mono text-xs tabular-nums text-ink-faint">
          {freshness.verified_at
            ? `${formatDate(freshness.verified_at)} 확인`
            : freshness.days_since_verified === null
              ? '확인 이력 없음'
              : `작성 후 ${freshness.days_since_verified}일`}
        </p>
      </section>

      <section className="mt-6 border-t border-border-subtle pt-6">
        <Link
          href={`/@${author.handle}`}
          className="-mx-2 flex items-center gap-2.5 rounded px-2 py-1.5 transition-colors hover:bg-surface-2"
        >
          <Avatar
            handle={author.handle}
            displayName={author.display_name}
            src={author.avatar_url}
            size={32}
          />
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium text-ink">
              {author.display_name}
            </span>
            <span className="block truncate text-xs text-ink-faint">@{author.handle}</span>
          </span>
        </Link>
      </section>

      {/* 목차는 있을 때만. 없다고 자리를 비워 두지는 않는다 (위가 이미 채운다). */}
      {toc.length >= 2 && (
        <section className="mt-6 border-t border-border-subtle pt-6">
          <TableOfContents items={toc} />
        </section>
      )}
    </div>
  )
}
