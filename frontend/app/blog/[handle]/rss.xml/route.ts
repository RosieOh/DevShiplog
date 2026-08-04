import { getRssSource, SITE_NAME, SITE_URL } from '@/lib/api/public'

/**
 * 블로그별 RSS 피드.
 *
 * 이 제품은 원래 "남의 블로그 RSS 를 읽어 톤을 학습"하는 도구였다.
 * 이제 우리가 발행처이므로 내보내는 쪽이 된다.
 */
export const revalidate = 600

function escapeXml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

export async function GET(
  _request: Request,
  { params }: { params: { handle: string } }
) {
  const handle = decodeURIComponent(params.handle)
  const source = await getRssSource(handle)

  if (!source) {
    return new Response('Not found', { status: 404 })
  }

  const blogUrl = `${SITE_URL}/@${source.author.handle}`
  const items = source.items
    .map((item) => {
      const link = `${SITE_URL}${item.url}`
      return `    <item>
      <title>${escapeXml(item.title)}</title>
      <link>${escapeXml(link)}</link>
      <guid isPermaLink="true">${escapeXml(link)}</guid>
      ${item.summary ? `<description>${escapeXml(item.summary)}</description>` : ''}
      ${item.published_at ? `<pubDate>${new Date(item.published_at).toUTCString()}</pubDate>` : ''}
    </item>`
    })
    .join('\n')

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${escapeXml(source.author.display_name)} — ${SITE_NAME}</title>
    <link>${escapeXml(blogUrl)}</link>
    <description>${escapeXml(source.author.bio || `${source.author.display_name}님의 기술 블로그`)}</description>
    <language>ko</language>
    <atom:link href="${escapeXml(`${blogUrl}/rss.xml`)}" rel="self" type="application/rss+xml"/>
${items}
  </channel>
</rss>`

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/rss+xml; charset=utf-8',
      'Cache-Control': 'public, max-age=600, stale-while-revalidate=3600',
    },
  })
}
