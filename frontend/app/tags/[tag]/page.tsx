import type { Metadata } from 'next'
import PostCard from '@/components/blog/PostCard'
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
    <div className="bg-canvas min-h-screen">
      <div className="mx-auto max-w-[820px] px-[5%] py-12">
        <header className="border-b border-black/10 pb-8">
          <h1 className="text-4xl font-bold tracking-tight text-ink">#{tag}</h1>
          <p className="mt-2 text-ink-muted">{posts.length}개의 글</p>
        </header>

        <main>
          {posts.length > 0 ? (
            posts.map((post) => <PostCard key={post.id} post={post} />)
          ) : (
            <p className="py-16 text-center text-ink-muted">이 태그의 글이 아직 없습니다.</p>
          )}
        </main>
      </div>
    </div>
  )
}
