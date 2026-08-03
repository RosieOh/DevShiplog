/**
 * 공개 콘텐츠 조회 — 서버 전용.
 *
 * 이 경로만큼은 클라이언트에서 베어러 토큰으로 가져오면 안 된다.
 * 검색 크롤러와 SNS 미리보기 봇은 로그인도 없고 JS 실행도 기대할 수 없기 때문에,
 * 공개 글은 반드시 서버에서 렌더링돼야 색인된다.
 *
 * 캐시는 태그 기반으로 무효화한다 (발행 시 revalidateTag).
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
export const SITE_NAME = 'Devshiplog'

export interface Author {
  handle: string
  display_name: string
  avatar_url: string | null
  bio: string | null
}

export interface PostCard {
  id: string
  slug: string
  title: string
  summary: string | null
  cover_url: string | null
  published_at: string | null
  like_count: number
  comment_count: number
  tags: string[]
  author: Author
  url: string
}

export interface CommentNode {
  id: string
  body: string | null
  deleted: boolean
  created_at: string | null
  author: Author | null
  is_mine: boolean
  replies: CommentNode[]
}

export interface SeriesNavData {
  name: string
  url: string
  /** 공개된 글만 세어서 매긴 순번. 중간 편을 내려도 번호가 건너뛰지 않는다. */
  position: number
  total: number
  previous: { title: string; url: string } | null
  next: { title: string; url: string } | null
}

export interface PostDetail extends PostCard {
  content_md: string
  view_count: number
  comments: CommentNode[]
  is_liked: boolean
  is_following_author: boolean
  is_mine: boolean
  series: SeriesNavData | null
}

export interface BlogHome extends Author {
  post_count: number
  follower_count: number
  following_count: number
  series: { slug: string; name: string; post_count: number }[]
  is_following: boolean
  is_me: boolean
}

export interface PostList {
  items: PostCard[]
  has_more: boolean
}

/** 캐시 태그 — 발행/수정 시 이 태그를 무효화한다. */
export const cacheTags = {
  feed: 'feed',
  blog: (handle: string) => `blog:${handle}`,
  post: (handle: string, slug: string) => `post:${handle}:${slug}`,
}

interface FetchOptions {
  tags?: string[]
  revalidate?: number
}

async function getJson<T>(path: string, options: FetchOptions = {}): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/public${path}`, {
      next: {
        // 발행 시 태그로 즉시 무효화하되, 안전망으로 시간 기반 재검증도 둔다.
        revalidate: options.revalidate ?? 60,
        tags: options.tags,
      },
    })
    if (res.status === 404) return null
    if (!res.ok) {
      console.error(`public API ${path} → ${res.status}`)
      return null
    }
    return (await res.json()) as T
  } catch (error) {
    // 백엔드가 죽어도 페이지는 "없음" 으로 뜨는 편이 500 보다 낫다.
    console.error(`public API ${path} 실패:`, error)
    return null
  }
}

export type FeedSort = 'recent' | 'trending' | 'recommended' | 'following'
export type FeedPeriod = 'week' | 'month' | 'year' | 'all'

export function getFeed(
  params: {
    sort?: FeedSort
    period?: FeedPeriod
    tag?: string
    limit?: number
    offset?: number
  } = {}
) {
  const q = new URLSearchParams()
  if (params.sort) q.set('sort', params.sort)
  if (params.period) q.set('period', params.period)
  if (params.tag) q.set('tag', params.tag)
  q.set('limit', String(params.limit ?? 20))
  q.set('offset', String(params.offset ?? 0))
  return getJson<PostList>(`/feed?${q}`, { tags: [cacheTags.feed], revalidate: 30 })
}

export function searchPosts(query: string, limit = 20) {
  return getJson<PostList>(`/search?q=${encodeURIComponent(query)}&limit=${limit}`, {
    revalidate: 0,
  })
}

export function getPopularTags(limit = 30) {
  return getJson<{ name: string; display_name: string; post_count: number }[]>(
    `/tags?limit=${limit}`,
    { tags: [cacheTags.feed], revalidate: 300 }
  )
}

export function getBlog(handle: string) {
  return getJson<BlogHome>(`/blogs/${encodeURIComponent(handle)}`, {
    tags: [cacheTags.blog(handle)],
  })
}

export function getBlogPosts(handle: string, limit = 20, offset = 0) {
  return getJson<PostList>(
    `/blogs/${encodeURIComponent(handle)}/posts?limit=${limit}&offset=${offset}`,
    { tags: [cacheTags.blog(handle)] }
  )
}

export function getPost(handle: string, slug: string) {
  return getJson<PostDetail>(
    `/blogs/${encodeURIComponent(handle)}/posts/${encodeURIComponent(slug)}`,
    { tags: [cacheTags.post(handle, slug)] }
  )
}

export function getSeries(handle: string, seriesSlug: string) {
  return getJson<{
    slug: string
    name: string
    description: string | null
    author: Author
    items: PostCard[]
  }>(`/blogs/${encodeURIComponent(handle)}/series/${encodeURIComponent(seriesSlug)}`, {
    tags: [cacheTags.blog(handle)],
  })
}

export function getSitemapEntries() {
  // 발행하면 사이트맵도 함께 갱신돼야 새 글이 바로 색인 대상이 된다.
  return getJson<{ url: string; updated_at: string | null }[]>('/sitemap', {
    tags: [cacheTags.feed],
    revalidate: 3600,
  })
}

export function getRssSource(handle: string) {
  return getJson<{
    author: Author
    items: { title: string; url: string; summary: string | null; published_at: string | null }[]
  }>(`/blogs/${encodeURIComponent(handle)}/rss`, { tags: [cacheTags.blog(handle)] })
}

/**
 * 업로드 주소를 절대 URL 로.
 *
 * 백엔드는 '/uploads/...' 상대 경로를 준다(도메인이 바뀌어도 DB 가 안 깨지게).
 * 하지만 OG 태그·JSON-LD 처럼 남의 서버가 읽는 자리에는 절대 주소가 필요하다.
 */
export function absoluteUrl(path: string): string {
  return /^https?:\/\//.test(path) ? path : `${SITE_URL}${path.startsWith('/') ? '' : '/'}${path}`
}

/** 날짜를 화면용 문자열로. 서버·클라이언트 렌더 결과가 어긋나지 않도록 UTC 고정. */
export function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getUTCFullYear()}. ${d.getUTCMonth() + 1}. ${d.getUTCDate()}.`
}
