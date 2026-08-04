'use client'

import { useEffect, useState } from 'react'
import type { TocItem } from '@/lib/toc'

/**
 * 글 옆 목차.
 *
 * 목록 자체는 서버에서 받은 데이터로 그리고, 클라이언트는 "지금 어디를 읽고 있는지"만
 * 표시한다. 그래서 JS 가 없어도 목차 링크는 동작한다.
 */
export default function TableOfContents({ items }: { items: TocItem[] }) {
  const [activeId, setActiveId] = useState<string | null>(items[0]?.id ?? null)

  useEffect(() => {
    if (items.length === 0) return

    const headings = items
      .map((item) => document.getElementById(item.id))
      .filter((el): el is HTMLElement => el !== null)
    if (headings.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        // 화면 상단에 걸린 것 중 가장 아래 것을 현재 위치로 본다.
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActiveId(visible[0].target.id)
      },
      // 헤더(64px) 아래부터 화면 절반까지를 "읽는 중" 영역으로 본다.
      { rootMargin: '-72px 0px -55% 0px', threshold: 0 }
    )

    headings.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [items])

  if (items.length < 2) return null

  return (
    <nav
      aria-label="목차"
      className="sticky top-24 max-h-[calc(100vh-8rem)] overflow-y-auto border-l border-border pl-4"
    >
      <p className="mb-3 text-xs font-bold uppercase tracking-wider text-ink-faint">목차</p>
      <ul className="space-y-2 text-sm">
        {items.map((item) => {
          const active = item.id === activeId
          return (
            <li key={item.id} style={{ paddingLeft: (item.level - 2) * 12 }}>
              <a
                href={`#${item.id}`}
                aria-current={active ? 'location' : undefined}
                className={`block leading-snug transition-colors ${
                  active ? 'font-bold text-ink' : 'text-ink-faint hover:text-ink'
                }`}
              >
                {item.text}
              </a>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
