import Link from 'next/link'
import type { SeriesNavData } from '@/lib/api/public'

/**
 * 시리즈 앞뒤 네비게이션.
 *
 * 연재의 값어치는 목록이 아니라 여기에 있다. 3편을 다 읽은 사람이 4편으로 갈
 * 길이 없으면 묶어 놓은 의미가 없다.
 */
export default function SeriesNav({ series }: { series: SeriesNavData }) {
  return (
    <nav
      aria-label="시리즈"
      className="rounded border border-border bg-surface p-5 md:p-6"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Link
          href={series.url}
          // 문장 속 링크가 아니라 그 자체로 누르는 표적이다. 44px 을 확보한다.
          className="inline-flex min-h-touch items-center text-lg font-bold text-ink hover:underline underline-offset-4"
        >
          {series.name}
        </Link>
        <span className="text-sm tabular-nums text-ink-faint">
          {series.position} / {series.total}
        </span>
      </div>

      {/* 진행도. 숫자만으로는 "얼마나 남았는지" 가 한눈에 안 들어온다. */}
      <div
        className="mt-3 h-1 w-full overflow-hidden rounded-full bg-surface-2"
        role="presentation"
      >
        <div
          className="h-full rounded-full bg-accent-text"
          style={{ width: `${(series.position / Math.max(series.total, 1)) * 100}%` }}
        />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {series.previous ? (
          <Link
            href={series.previous.url}
            className="group flex min-h-touch flex-col justify-center rounded border border-border px-4 py-3 transition-colors hover:bg-bg"
          >
            <span className="text-xs font-bold uppercase tracking-wider text-ink-faint">
              이전 글
            </span>
            <span className="mt-1 line-clamp-1 text-sm font-medium text-ink">
              {series.previous.title}
            </span>
          </Link>
        ) : (
          <span aria-hidden="true" className="hidden sm:block" />
        )}

        {series.next && (
          <Link
            href={series.next.url}
            className="group flex min-h-touch flex-col justify-center rounded border border-border px-4 py-3 text-right transition-colors hover:bg-bg sm:col-start-2"
          >
            <span className="text-xs font-bold uppercase tracking-wider text-ink-faint">
              다음 글
            </span>
            <span className="mt-1 line-clamp-1 text-sm font-medium text-ink">
              {series.next.title}
            </span>
          </Link>
        )}
      </div>
    </nav>
  )
}
