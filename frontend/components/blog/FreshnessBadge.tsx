import type { Freshness } from '@/lib/api/public'

/**
 * 이 글을 믿어도 되는지.
 *
 * 작성일이 아니라 **마지막으로 "지금도 된다" 고 확인한 시각**을 보여준다.
 * 작성일은 글이 맞는지와 상관이 없다 — 2년 전 글도 어제 다시 돌려봤다면 믿을 수 있다.
 */

const LEVELS = {
  fresh: {
    label: '검증됨',
    dot: 'bg-fresh',
    text: 'text-fresh',
    ring: 'border-fresh/30 bg-fresh/8',
  },
  aging: {
    label: '확인 필요',
    dot: 'bg-aging',
    text: 'text-aging',
    ring: 'border-aging/30 bg-aging/8',
  },
  stale: {
    label: '오래됨',
    dot: 'bg-stale',
    text: 'text-stale',
    ring: 'border-stale/30 bg-stale/8',
  },
  unverified: {
    label: '미검증',
    dot: 'bg-ink-faint',
    text: 'text-ink-faint',
    ring: 'border-border bg-surface-2',
  },
} as const

export function FreshnessDot({ freshness }: { freshness: Freshness }) {
  const level = LEVELS[freshness.level] ?? LEVELS.unverified
  return (
    <span className="inline-flex items-center gap-1.5">
      <span aria-hidden="true" className={`h-1.5 w-1.5 shrink-0 rounded-full ${level.dot}`} />
      <span className={`text-xs font-medium ${level.text}`}>{level.label}</span>
    </span>
  )
}

/**
 * 본문 위에 놓이는 상세 배너.
 *
 * fresh 일 때는 띄우지 않는다. "이 글은 괜찮습니다" 를 매번 말하면 배너가 흔해지고,
 * 정작 경고해야 할 때 아무도 안 본다.
 */
export default function FreshnessBanner({ freshness }: { freshness: Freshness }) {
  if (freshness.level === 'fresh') return null

  const level = LEVELS[freshness.level] ?? LEVELS.unverified
  const outdated = freshness.outdated ?? []

  return (
    <aside
      // stale 만 alert. aging·unverified 까지 스크린리더가 가로채면 소음이 된다.
      role={freshness.level === 'stale' ? 'alert' : undefined}
      className={`rounded border px-4 py-3 ${level.ring}`}
    >
      <div className="flex items-start gap-2.5">
        <span
          aria-hidden="true"
          className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${level.dot}`}
        />
        <div className="min-w-0">
          <p className={`text-sm font-bold ${level.text}`}>{level.label}</p>
          <p className="mt-0.5 text-sm leading-relaxed text-ink-muted">{freshness.reason}</p>

          {outdated.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {outdated.map((item) => (
                <li
                  key={item.name}
                  className="inline-flex items-center rounded border border-border bg-surface px-2 py-0.5 font-mono text-[11px] tabular-nums text-ink-muted"
                >
                  {item.name}@{item.version}
                  <span aria-hidden="true" className="mx-1 text-ink-faint">
                    →
                  </span>
                  <span className="text-ink">{item.latest_major}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </aside>
  )
}
