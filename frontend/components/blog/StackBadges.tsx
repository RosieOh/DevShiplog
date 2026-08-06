import Link from 'next/link'
import type { PostStack } from '@/lib/api/public'

/**
 * 글이 전제하는 기술과 버전.
 *
 * 태그와 나란히 두지 않는다. 태그는 "무엇에 관한 글인가" 이고 이건 "어느 환경에서
 * 확인된 절차인가" 다. 독자가 판단에 쓰는 정보라 제목 근처에 있어야 한다.
 *
 * 등폭 글꼴을 쓰는 것은 장식이 아니다. 버전은 숫자이고, 여러 개가 세로로 놓일 때
 * 자릿수가 맞아야 훑어진다.
 */
export default function StackBadges({
  stacks,
  size = 'default',
}: {
  stacks: PostStack[]
  size?: 'default' | 'compact'
}) {
  if (stacks.length === 0) return null

  const compact = size === 'compact'

  return (
    <ul
      className={`flex flex-wrap items-center ${compact ? 'gap-1' : 'gap-1.5'}`}
      aria-label="이 글이 전제하는 기술 스택"
    >
      {stacks.map((stack) => (
        <li key={stack.name}>
          <Link
            href={`/stacks/${encodeURIComponent(stack.name)}${
              stack.version ? `?version=${encodeURIComponent(stack.version)}` : ''
            }`}
            className={`inline-flex items-center rounded border border-border bg-surface-2 font-mono tabular-nums text-ink-muted transition-colors hover:border-ink-faint hover:text-ink ${
              compact ? 'min-h-[26px] px-1.5 text-[11px]' : 'min-h-[30px] px-2 text-xs'
            }`}
          >
            {stack.name}
            {stack.version && (
              <>
                <span aria-hidden="true" className="mx-0.5 text-ink-faint">
                  @
                </span>
                {stack.version}
              </>
            )}
          </Link>
        </li>
      ))}
    </ul>
  )
}
