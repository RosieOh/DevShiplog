'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { apiClient } from '@/lib/api/client'
import { useToastStore } from '@/store/toastStore'

interface Signals {
  works: number
  broken: number
  my_signal: 'works' | 'broken' | null
}

/**
 * "따라 해봤다" 신호.
 *
 * 좋아요와 다르다. 좋아요는 "좋았다" 고 이건 "해봤다" 다.
 * 수는 훨씬 적지만 작성자에게도 다음 독자에게도 훨씬 무거운 신호다.
 *
 * "안 됐어요" 를 댓글로 받으면 묻힌다. 세 개가 달려도 작성자는 모르고,
 * 알아도 여러 글 중 어느 것부터 고쳐야 할지 판단할 수 없다.
 */
export default function WorksSignal({
  postId,
  initial,
  isMine,
}: {
  postId: string
  initial: Signals
  isMine: boolean
}) {
  const { status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [signals, setSignals] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [noteOpen, setNoteOpen] = useState(false)
  const [note, setNote] = useState('')

  // 자기 글에는 안 보여준다. 자기 확인은 검증 버튼으로 한다.
  if (isMine) return null

  const send = async (kind: 'works' | 'broken', withNote?: string) => {
    if (status !== 'authenticated') {
      router.push('/auth/login')
      return
    }
    try {
      setBusy(true)
      const next = await apiClient.post<Signals>(`/api/v1/posts/${postId}/signal`, {
        kind,
        note: withNote || undefined,
      })
      setSignals(next)
      setNoteOpen(false)
      setNote('')
      addToast({
        message: kind === 'works' ? '알려주셔서 고맙습니다.' : '작성자에게 전달했습니다.',
        type: 'success',
      })
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '전송에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setBusy(false)
    }
  }

  const chosen = signals.my_signal

  return (
    <section
      aria-labelledby="works-signal-title"
      className="rounded border border-border bg-surface-2 p-4 md:p-5"
    >
      <h2 id="works-signal-title" className="text-sm font-bold text-ink">
        따라 해보셨나요?
      </h2>
      <p className="mt-1 text-sm leading-relaxed text-ink-muted">
        결과를 알려주시면 다음 사람이 이 글을 믿어도 되는지 판단할 수 있습니다.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => void send('works')}
          disabled={busy}
          aria-pressed={chosen === 'works'}
          className={`inline-flex min-h-touch items-center gap-2 rounded border px-4 text-sm font-medium transition-colors disabled:opacity-60 ${
            chosen === 'works'
              ? 'border-fresh bg-fresh/10 text-fresh'
              : 'border-border bg-surface text-ink-muted hover:border-ink-faint hover:text-ink'
          }`}
        >
          잘 됐어요
          {signals.works > 0 && (
            <span className="font-mono text-xs tabular-nums">{signals.works}</span>
          )}
        </button>

        <button
          type="button"
          onClick={() => {
            if (status !== 'authenticated') {
              router.push('/auth/login')
              return
            }
            setNoteOpen((open) => !open)
          }}
          disabled={busy}
          aria-pressed={chosen === 'broken'}
          aria-expanded={noteOpen}
          className={`inline-flex min-h-touch items-center gap-2 rounded border px-4 text-sm font-medium transition-colors disabled:opacity-60 ${
            chosen === 'broken'
              ? 'border-stale bg-stale/10 text-stale'
              : 'border-border bg-surface text-ink-muted hover:border-ink-faint hover:text-ink'
          }`}
        >
          안 됐어요
          {signals.broken > 0 && (
            <span className="font-mono text-xs tabular-nums">{signals.broken}</span>
          )}
        </button>
      </div>

      {noteOpen && (
        <div className="mt-3">
          <label htmlFor="signal-note" className="block text-sm font-medium text-ink">
            어디서 막혔는지 알려주시면 고치는 데 큰 도움이 됩니다 (선택)
          </label>
          <textarea
            id="signal-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            maxLength={1000}
            placeholder="예: Node 22 에서는 이 옵션이 없어졌습니다"
            className="mt-2 w-full rounded border border-border bg-surface p-3 text-sm text-ink"
          />
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={() => void send('broken', note)}
              disabled={busy}
              className="inline-flex min-h-touch items-center rounded bg-ink px-5 text-sm font-bold text-bg transition-opacity hover:opacity-85 disabled:opacity-50"
            >
              보내기
            </button>
            <button
              type="button"
              onClick={() => setNoteOpen(false)}
              className="inline-flex min-h-touch items-center rounded px-4 text-sm text-ink-muted hover:text-ink"
            >
              취소
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
