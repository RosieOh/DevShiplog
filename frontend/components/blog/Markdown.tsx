import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * 공개 글 본문 렌더러 (서버 컴포넌트).
 *
 * rehype-raw 를 쓰지 않는다. 남이 쓴 마크다운을 HTML 그대로 통과시키면
 * 저장형 XSS 가 열린다. react-markdown 기본값은 원시 HTML 을 무시한다.
 */
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="prose max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
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
          // eslint-disable-next-line @next/next/no-img-element
          img: ({ src, alt }) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={src} alt={alt ?? ''} loading="lazy" className="rounded-2xl max-w-full h-auto" />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
