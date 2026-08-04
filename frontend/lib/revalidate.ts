/**
 * 쓰기 동작 후 공개 페이지 캐시를 깨는 클라이언트 헬퍼.
 *
 * 실패해도 예외를 던지지 않는다. 캐시 무효화가 안 되면 최대 revalidate 시간만큼
 * 낡은 화면이 보일 뿐이고, 그것 때문에 발행 자체가 실패한 것처럼 보이면 안 된다.
 */
export async function revalidateContent(tags: string[]): Promise<void> {
  if (tags.length === 0) return
  try {
    await fetch('/api/revalidate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tags }),
    })
  } catch {
    // 무시 — 시간 기반 재검증이 안전망이다.
  }
}

/** `/@handle/slug` 형태의 주소에서 캐시 태그를 만든다. */
export function tagsForPostUrl(url: string | null | undefined): string[] {
  const tags = ['feed']
  if (!url) return tags

  const match = /^\/@([^/]+)(?:\/(.+))?$/.exec(url)
  if (!match) return tags

  const [, handle, slug] = match
  tags.push(`blog:${handle}`)
  if (slug) tags.push(`post:${handle}:${decodeURIComponent(slug)}`)
  return tags
}
