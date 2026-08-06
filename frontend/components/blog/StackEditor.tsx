'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api/client'

export interface StackDraft {
  name: string
  version: string | null
  confidence?: string
  evidence?: string
}

/**
 * 발행 전 기술 스택 확인.
 *
 * 본문에서 자동으로 뽑되 **확정은 작성자가 한다.** 자동으로 확정해 버리면 틀린
 * 메타데이터가 조용히 퍼지고, 그건 없는 것보다 나쁘다 — 독자가 잘못된 근거로
 * 글을 믿게 된다.
 *
 * 그래서 어디서 찾았는지(evidence)를 같이 보여준다. 작성자가 "이건 아닌데" 를
 * 판단하려면 근거가 필요하다.
 */
export default function StackEditor({
  contentMd,
  value,
  onChange,
}: {
  contentMd: string
  value: StackDraft[]
  onChange: (next: StackDraft[]) => void
}) {
  const [loading, setLoading] = useState(false)
  const [suggested, setSuggested] = useState(false)
  const [name, setName] = useState('')
  const [version, setVersion] = useState('')

  useEffect(() => {
    // 한 번만 제안한다. 본문을 고칠 때마다 사용자가 지운 항목이 되살아나면 안 된다.
    if (suggested || value.length > 0 || !contentMd.trim()) return
    setSuggested(true)
    setLoading(true)
    apiClient
      .post<{ stacks: StackDraft[] }>('/api/v1/posts/stacks/suggest', { content_md: contentMd })
      .then((result) => onChange(result.stacks))
      .catch(() => undefined)
      .finally(() => setLoading(false))
  }, [contentMd, suggested, value.length, onChange])

  const add = () => {
    const cleaned = name.trim().toLowerCase()
    if (!cleaned || value.some((s) => s.name === cleaned)) return
    onChange([...value, { name: cleaned, version: version.trim() || null }])
    setName('')
    setVersion('')
  }

  return (
    <section>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">기술 스택</h3>
        {loading && <span className="text-xs text-ink-faint">본문에서 찾는 중...</span>}
      </div>
      <p className="mt-1 text-xs leading-relaxed text-ink-muted">
        이 글이 전제하는 환경입니다. 독자가 자기 환경과 맞는지 판단하고, 나중에 버전이
        올라가면 갱신이 필요하다고 알려드립니다.
      </p>

      {value.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {value.map((stack, index) => (
            <li
              key={stack.name}
              className="flex items-center gap-2 rounded border border-border bg-bg px-3 py-2"
            >
              <span className="font-mono text-sm text-ink">{stack.name}</span>
              <input
                type="text"
                value={stack.version ?? ''}
                onChange={(e) => {
                  const next = [...value]
                  next[index] = { ...stack, version: e.target.value.trim() || null }
                  onChange(next)
                }}
                placeholder="버전"
                aria-label={`${stack.name} 버전`}
                className="w-20 rounded border border-border bg-surface px-2 py-1 font-mono text-xs tabular-nums text-ink"
              />
              {stack.evidence && (
                <span className="min-w-0 flex-1 truncate text-xs text-ink-faint">
                  {stack.evidence}
                </span>
              )}
              <button
                type="button"
                onClick={() => onChange(value.filter((_, i) => i !== index))}
                aria-label={`${stack.name} 제거`}
                className="ml-auto grid h-8 w-8 shrink-0 place-items-center rounded text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-2 flex gap-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              add()
            }
          }}
          placeholder="react"
          aria-label="기술 이름"
          className="min-h-touch min-w-0 flex-1 rounded border border-border bg-bg px-3 font-mono text-sm text-ink"
        />
        <input
          type="text"
          value={version}
          onChange={(e) => setVersion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              add()
            }
          }}
          placeholder="18.3"
          aria-label="버전"
          className="min-h-touch w-24 rounded border border-border bg-bg px-3 font-mono text-sm tabular-nums text-ink"
        />
        <button
          type="button"
          onClick={add}
          className="inline-flex min-h-touch shrink-0 items-center rounded border border-border bg-surface px-4 text-sm font-medium text-ink hover:bg-bg"
        >
          추가
        </button>
      </div>
    </section>
  )
}
