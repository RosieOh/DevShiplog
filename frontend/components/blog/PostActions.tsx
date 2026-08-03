'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { socialService } from '@/features/social/services/socialService'
import { useToastStore } from '@/store/toastStore'
import { AlertIcon, CheckCircleIcon } from '@/components/ui/icons'

interface Props {
  postId: string
  initialLiked: boolean
  initialLikeCount: number
  authorHandle: string
  isMine: boolean
}

const REPORT_REASONS = [
  { value: 'spam', label: '스팸/광고' },
  { value: 'abuse', label: '욕설/괴롭힘' },
  { value: 'sensitive', label: '민감정보 노출' },
  { value: 'copyright', label: '저작권 침해' },
  { value: 'other', label: '기타' },
] as const

export default function PostActions({
  postId,
  initialLiked,
  initialLikeCount,
  authorHandle,
  isMine,
}: Props) {
  const { status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [liked, setLiked] = useState(initialLiked)
  const [count, setCount] = useState(initialLikeCount)
  const [busy, setBusy] = useState(false)
  const [reporting, setReporting] = useState(false)

  const requireLogin = () => {
    if (status !== 'authenticated') {
      router.push('/auth/login')
      return true
    }
    return false
  }

  const onLike = async () => {
    if (requireLogin()) return
    // 낙관적 갱신. 실패하면 되돌린다.
    const prev = { liked, count }
    setLiked(!liked)
    setCount(liked ? count - 1 : count + 1)
    try {
      setBusy(true)
      const result = await socialService.toggleLike(postId)
      setLiked(result.liked)
      setCount(result.like_count)
    } catch (err) {
      setLiked(prev.liked)
      setCount(prev.count)
      addToast({
        message: err instanceof Error ? err.message : '요청에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setBusy(false)
    }
  }

  const onReport = async (reason: string) => {
    try {
      const result = await socialService.report('post', postId, reason)
      setReporting(false)
      addToast({
        message: result.auto_hidden
          ? '신고가 접수되었고 검토 전까지 글이 가려집니다.'
          : '신고가 접수되었습니다.',
        type: 'success',
      })
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '신고에 실패했습니다.',
        type: 'error',
      })
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 border-t border-black/10 pt-8">
      <button
        type="button"
        onClick={onLike}
        disabled={busy}
        aria-pressed={liked}
        className={`inline-flex min-h-touch items-center gap-2 rounded-full px-6 font-semibold transition-colors disabled:opacity-60 ${
          liked ? 'bg-accent text-ink' : 'border border-black/10 bg-surface text-ink hover:bg-canvas'
        }`}
      >
        <CheckCircleIcon className="h-5 w-5" />
        좋아요 {count}
      </button>

      {!isMine && (
        <div className="relative">
          <button
            type="button"
            onClick={() => (requireLogin() ? null : setReporting((v) => !v))}
            aria-expanded={reporting}
            className="inline-flex min-h-touch items-center gap-1.5 rounded-full px-4 text-sm text-ink-muted transition-colors hover:text-ink"
          >
            <AlertIcon className="h-4 w-4" />
            신고
          </button>

          {reporting && (
            <div
              role="dialog"
              aria-label="신고 사유 선택"
              className="absolute right-0 z-20 mt-2 w-56 rounded-2xl border border-black/10 bg-surface p-2 shadow-lg shadow-black/5"
            >
              {REPORT_REASONS.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => onReport(r.value)}
                  className="flex min-h-touch w-full items-center rounded-xl px-3 text-left text-sm text-ink transition-colors hover:bg-canvas"
                >
                  {r.label}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setReporting(false)}
                className="flex min-h-touch w-full items-center rounded-xl px-3 text-left text-sm text-ink-muted transition-colors hover:bg-canvas"
              >
                취소
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
