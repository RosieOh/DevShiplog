import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { formatDate, getSeries, SITE_NAME, SITE_URL } from '@/lib/api/public'

interface Props {
  params: { handle: string; seriesSlug: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const handle = decodeURIComponent(params.handle)
  const seriesSlug = decodeURIComponent(params.seriesSlug)
  const series = await getSeries(handle, seriesSlug)
  if (!series) return { title: '시리즈를 찾을 수 없습니다' }

  const title = `${series.name} — ${series.author.display_name}`
  const description = series.description || `${series.name} 연재 모음`
  return {
    title,
    description,
    alternates: { canonical: `${SITE_URL}/@${handle}/series/${encodeURIComponent(seriesSlug)}` },
    openGraph: { type: 'website', siteName: SITE_NAME, title, description },
  }
}

export default async function SeriesPage({ params }: Props) {
  const handle = decodeURIComponent(params.handle)
  const seriesSlug = decodeURIComponent(params.seriesSlug)
  const series = await getSeries(handle, seriesSlug)

  if (!series) notFound()

  return (
    <div className="bg-canvas min-h-screen">
      <div className="mx-auto max-w-[760px] px-[5%] py-12">
        <header className="border-b border-black/10 pb-8">
          <Link
            href={`/@${handle}`}
            className="text-sm text-ink-muted transition-colors hover:text-ink"
          >
            ← {series.author.display_name}
          </Link>
          <h1 className="mt-4 text-4xl font-bold tracking-tight text-ink">{series.name}</h1>
          {series.description && (
            <p className="mt-3 leading-relaxed text-ink-muted">{series.description}</p>
          )}
          <p className="mt-3 text-sm text-ink-muted">{series.items.length}편</p>
        </header>

        <ol className="mt-8 space-y-1">
          {series.items.map((post, index) => (
            <li key={post.id}>
              <Link
                href={post.url}
                className="group flex gap-4 rounded-2xl px-4 py-5 transition-colors hover:bg-surface"
              >
                <span className="pt-0.5 text-sm font-semibold tabular-nums text-ink-muted">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="flex-1">
                  <span className="block font-semibold text-ink group-hover:underline underline-offset-4">
                    {post.title}
                  </span>
                  <time
                    className="mt-1 block text-sm text-ink-muted"
                    dateTime={post.published_at ?? undefined}
                  >
                    {formatDate(post.published_at)}
                  </time>
                </span>
              </Link>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
