import type { Metadata } from 'next'
import Link from 'next/link'
import PostRow from '@/components/blog/PostRow'
import { getPostsByStack, SITE_NAME, SITE_URL, type StackSort } from '@/lib/api/public'

interface Props {
  params: { name: string }
  searchParams: { version?: string; sort?: string }
}

const SORTS: { key: StackSort; label: string; hint: string }[] = [
  { key: 'fresh_first', label: '검증 최신순', hint: '가장 최근에 동작이 확인된 글부터' },
  { key: 'recent', label: '작성 최신순', hint: '가장 최근에 쓰인 글부터' },
  { key: 'trending', label: '반응순', hint: '좋아요와 댓글이 많은 글부터' },
]

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const name = decodeURIComponent(params.name)
  const version = searchParams.version
  const title = version ? `${name} ${version} 글 모음` : `${name} 글 모음`

  return {
    title: `${title} — ${SITE_NAME}`,
    description: `${name}${
      version ? ` ${version}` : ''
    } 로 확인된 기술 글. 마지막 검증 시각과 함께 봅니다.`,
    alternates: { canonical: `${SITE_URL}/stacks/${encodeURIComponent(name)}` },
  }
}

export default async function StackPage({ params, searchParams }: Props) {
  const name = decodeURIComponent(params.name)
  const version = searchParams.version
  const sort = (SORTS.find((s) => s.key === searchParams.sort)?.key ?? 'fresh_first') as StackSort

  const feed = await getPostsByStack(name, { version, sort })
  const posts = feed?.items ?? []

  const hrefFor = (nextSort: StackSort, nextVersion?: string) => {
    const q = new URLSearchParams()
    if (nextVersion) q.set('version', nextVersion)
    if (nextSort !== 'fresh_first') q.set('sort', nextSort)
    const query = q.toString()
    return `/stacks/${encodeURIComponent(name)}${query ? `?${query}` : ''}`
  }

  // 결과에 실제로 등장한 버전만 필터로 준다.
  // 있지도 않은 버전을 눌러 빈 화면을 보게 하지 않는다.
  const versions = Array.from(
    new Set(
      posts
        .flatMap((post) => post.stacks)
        .filter((stack) => stack.name === name && stack.version)
        .map((stack) => stack.version as string)
    )
  ).sort((a, b) => b.localeCompare(a, undefined, { numeric: true }))

  return (
    <div className="mx-auto w-full max-w-shell px-4 py-8 md:px-6">
      <div className="mx-auto w-full max-w-content lg:mx-0">
      <header className="border-b border-border pb-6">
        <p className="text-xs font-bold uppercase tracking-wider text-ink-faint">기술 스택</p>
        <h1 className="mt-2 font-mono text-3xl font-bold tracking-tight text-ink">
          {name}
          {version && <span className="text-ink-faint">@{version}</span>}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-muted">
          이 스택으로 쓰인 글입니다. 작성일이 아니라{' '}
          <b className="font-bold text-ink">마지막으로 동작이 확인된 시각</b> 기준으로
          정렬합니다 — 최근에 쓴 글이라고 지금도 되는 것은 아니기 때문입니다.
        </p>
      </header>

      {versions.length > 0 && (
        <nav aria-label="버전" className="mt-6 flex flex-wrap items-center gap-2">
          <Link
            href={hrefFor(sort)}
            aria-current={!version ? 'true' : undefined}
            className={`inline-flex min-h-[34px] items-center rounded border px-3 font-mono text-xs transition-colors ${
              !version
                ? 'border-ink bg-ink text-bg'
                : 'border-border bg-surface text-ink-muted hover:text-ink'
            }`}
          >
            전체
          </Link>
          {versions.map((v) => (
            <Link
              key={v}
              href={hrefFor(sort, v)}
              aria-current={version === v ? 'true' : undefined}
              className={`inline-flex min-h-[34px] items-center rounded border px-3 font-mono text-xs tabular-nums transition-colors ${
                version === v
                  ? 'border-ink bg-ink text-bg'
                  : 'border-border bg-surface text-ink-muted hover:text-ink'
              }`}
            >
              {v}
            </Link>
          ))}
        </nav>
      )}

      <nav aria-label="정렬" className="mt-4 flex flex-wrap items-center gap-4 border-b border-border pb-4">
        {SORTS.map((option) => (
          <Link
            key={option.key}
            href={hrefFor(option.key, version)}
            aria-current={sort === option.key ? 'page' : undefined}
            title={option.hint}
            className={`inline-flex min-h-touch items-center text-sm transition-colors ${
              sort === option.key
                ? 'font-bold text-ink'
                : 'font-medium text-ink-faint hover:text-ink'
            }`}
          >
            {option.label}
          </Link>
        ))}
      </nav>

      {posts.length === 0 ? (
        <div className="mt-8 rounded border border-border bg-surface px-6 py-16 text-center">
          <p className="text-ink">
            <span className="font-mono">{name}</span>
            {version && <span className="font-mono text-ink-faint">@{version}</span>} 글이 아직
            없습니다.
          </p>
          <Link
            href="/drafts/new"
            className="mt-5 inline-flex min-h-touch items-center rounded bg-ink px-6 text-sm font-bold text-bg transition-opacity hover:opacity-85"
          >
            첫 글 쓰기
          </Link>
        </div>
      ) : (
        <div className="mt-6 divide-y divide-border-subtle">
          {posts.map((post) => (
            <PostRow key={post.id} post={post} />
          ))}
        </div>
      )}
    </div>
    </div>
  )
}
