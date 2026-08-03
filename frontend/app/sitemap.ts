import type { MetadataRoute } from 'next'
import { getSitemapEntries, SITE_URL } from '@/lib/api/public'

/**
 * 사이트맵.
 *
 * 블로그 플랫폼은 글이 늘어날수록 색인이 자산이 된다. 새 글이 내부 링크만으로
 * 발견되기를 기다리지 않고 직접 알린다.
 */
// 라우트 레벨 revalidate 를 두면 빌드 시점(글이 0개일 때) 데이터로 정적 생성되어 굳는다.
// 라우트는 요청마다 렌더하고, 실제 캐싱은 getSitemapEntries 의 태그 붙은 fetch 가 맡는다.
export const dynamic = 'force-dynamic'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: SITE_URL, changeFrequency: 'hourly', priority: 1 },
    { url: `${SITE_URL}/about`, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${SITE_URL}/terms`, changeFrequency: 'yearly', priority: 0.2 },
    { url: `${SITE_URL}/privacy`, changeFrequency: 'yearly', priority: 0.2 },
  ]

  const entries = await getSitemapEntries()
  const posts: MetadataRoute.Sitemap = (entries ?? []).map((entry) => ({
    url: `${SITE_URL}${entry.url}`,
    lastModified: entry.updated_at ? new Date(entry.updated_at) : undefined,
    changeFrequency: 'weekly',
    priority: 0.8,
  }))

  return [...staticRoutes, ...posts]
}
