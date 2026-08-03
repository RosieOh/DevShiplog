/**
 * 마크다운에서 목차를 뽑는다.
 *
 * 서버에서 만들어야 하는 이유: 본문 렌더도 서버에서 하므로 heading id 를 양쪽이
 * 같은 규칙으로 만들어야 앵커가 맞는다. 클라이언트에서 DOM 을 훑어 만들면
 * 첫 페인트에 목차가 비어 있고, 크롤러도 못 읽는다.
 */

export interface TocItem {
  id: string
  text: string
  level: number
}

/** 제목 텍스트 → 앵커 id. Markdown 렌더러와 반드시 같은 규칙을 써야 한다. */
export function headingId(text: string): string {
  return (
    text
      .trim()
      .toLowerCase()
      // 인라인 마크다운 기호 제거
      .replace(/[`*_~[\]()]/g, '')
      .replace(/\s+/g, '-')
      .replace(/[^\w가-힣-]/g, '')
      .replace(/-{2,}/g, '-')
      .replace(/^-|-$/g, '') || 'section'
  )
}

export function extractToc(markdown: string): TocItem[] {
  const lines = (markdown || '').split('\n')
  const items: TocItem[] = []
  const used = new Map<string, number>()
  let inFence = false

  for (const line of lines) {
    // 코드 블록 안의 `# 주석` 을 제목으로 오인하지 않는다.
    if (/^\s*```/.test(line)) {
      inFence = !inFence
      continue
    }
    if (inFence) continue

    const match = /^(#{2,3})\s+(.+?)\s*#*\s*$/.exec(line)
    if (!match) continue

    const level = match[1].length
    const text = match[2].replace(/[`*_]/g, '').trim()
    if (!text) continue

    // 같은 제목이 두 번 나오면 뒤에 번호를 붙여 앵커가 겹치지 않게 한다.
    const base = headingId(text)
    const seen = used.get(base) ?? 0
    used.set(base, seen + 1)

    items.push({ id: seen === 0 ? base : `${base}-${seen}`, text, level })
  }

  return items
}
