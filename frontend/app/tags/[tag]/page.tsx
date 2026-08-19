import type { Metadata } from 'next'
import PostRow from '@/components/blog/PostRow'
import { getFeed, SITE_NAME, SITE_URL } from '@/lib/api/public'

interface Props {
  params: { tag: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const tag = decodeURIComponent(params.tag)
  const title = `#${tag}`
  const description = `${tag} 태그가 달린 기술 글 모음`
  return {
    title,
    description,
    alternates: { canonical: `${SITE_URL}/tags/${encodeURIComponent(tag)}` },
    openGraph: { type: 'website', siteName: SITE_NAME, title, description },
  }
}

export default async function TagPage({ params }: Props) {
  const tag = decodeURIComponent(params.tag)
  const feed = await getFeed({ tag, limit: 30 })
  const posts = feed?.items ?? []

  return (
    <div className="bg-bg min-h-screen">
      <div className="mx-auto w-full max-w-shell px-4 py-12 md:px-6">
      <div className="mx-auto w-full max-w-content lg:mx-0">
        <header className="border-b border-border pb-8">
          <h1 className="text-4xl font-bold tracking-tight text-ink">#{tag}</h1>
          <p className="mt-2 text-ink-muted">{posts.length}개의 글</p>
        </header>

        <main>
          {posts.length > 0 ? (
            <div className="divide-y divide-border-subtle">
              {posts.map((post) => (
                <PostRow key={post.id} post={post} />
              ))}
            </div>
          ) : (
            <p className="py-16 text-center text-ink-muted">이 태그의 글이 아직 없습니다.</p>
          )}
        </main>
      </div>
    </div>
    </div>
  )
}
