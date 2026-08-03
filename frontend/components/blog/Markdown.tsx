import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { headingId } from '@/lib/toc'

/**
 * 공개 글 본문 렌더러 (서버 컴포넌트).
 *
 * rehype-raw 를 쓰지 않는다. 남이 쓴 마크다운을 HTML 그대로 통과시키면
 * 저장형 XSS 가 열린다. react-markdown 기본값은 원시 HTML 을 무시한다.
 */

/** 제목에 목차와 같은 규칙의 id 를 붙인다 (lib/toc.ts 와 짝). */
function useHeading(level: 2 | 3, counters: Map<string, number>) {
  const Tag = `h${level}` as 'h2' | 'h3'
  return function Heading({ children }: { children?: React.ReactNode }) {
    const text = extractText(children)
    const base = headingId(text)
    const seen = counters.get(base) ?? 0
    counters.set(base, seen + 1)
    const id = seen === 0 ? base : `${base}-${seen}`
    return (
      // scroll-mt 로 고정 헤더에 제목이 가려지지 않게 한다.
      <Tag id={id} className="scroll-mt-24">
        {children}
      </Tag>
    )
  }
}

function extractText(node: React.ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractText).join('')
  if (node && typeof node === 'object' && 'props' in node) {
    return extractText((node as { props: { children?: React.ReactNode } }).props.children)
  }
  return ''
}

export default function Markdown({ children }: { children: string }) {
  // 같은 제목이 반복될 때 목차와 동일한 방식으로 번호를 붙이기 위한 카운터
  const counters = new Map<string, number>()

  return (
    <div className="prose max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        /*
         * 문법 강조는 서버에서 끝낸다 (highlight.js 런타임을 브라우저로 보내지 않는다).
         * detect:false — 언어를 안 적은 블록까지 추측하면 로그·설정 파일이 엉뚱하게 칠해진다.
         * ignoreMissing:true — 모르는 언어 이름이 와도 예외 대신 그냥 강조를 건너뛴다.
         */
        rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]}
        components={{
          h2: useHeading(2, counters),
          h3: useHeading(3, counters),
          a: ({ href, children: linkChildren, ...props }) => {
            const external = Boolean(href && /^https?:\/\//.test(href))
            return (
              <a
                href={href}
                // 외부 링크는 새 탭 + 참조 차단 (tabnabbing 방지)
                {...(external ? { target: '_blank', rel: 'noopener noreferrer ugc' } : {})}
                {...props}
              >
                {linkChildren}
              </a>
            )
          },
          img: ({ src, alt }) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={src} alt={alt ?? ''} loading="lazy" className="rounded max-w-full h-auto" />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
