'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { socialService } from '@/features/social/services/socialService'
import { useToastStore } from '@/store/toastStore'
import { HeartIcon } from '@/components/ui/icons'

interface Props {
  postId: string
  initialLiked: boolean
  initialLikeCount: number
}

/**
 * 본문 왼쪽에 붙는 좋아요·공유 바.
 *
 * 넓은 화면에서만 나온다. 좁은 화면에서는 본문 아래 PostActions 가 같은 역할을 하므로
 * 여기까지 띄우면 같은 버튼이 두 번 보인다.
 */
export default function FloatingActions({ postId, initialLiked, initialLikeCount }: Props) {
  const { status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [liked, setLiked] = useState(initialLiked)
  const [count, setCount] = useState(initialLikeCount)
  const [busy, setBusy] = useState(false)
  const [visible, setVisible] = useState(false)

  // 첫 화면에서는 방해가 되지 않도록, 조금 내려간 뒤에 나타난다.
  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 320)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const onLike = async () => {
    if (status !== 'authenticated') {
      router.push('/auth/login')
      return
    }
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

  const onShare = async () => {
    const url = window.location.href
    try {
      if (navigator.share) {
        await navigator.share({ title: document.title, url })
        return
      }
      await navigator.clipboard.writeText(url)
      addToast({ message: '주소를 복사했습니다.', type: 'success' })
    } catch {
      // 사용자가 공유 시트를 닫은 경우 — 오류가 아니다.
    }
  }

  return (
    <div
      aria-hidden={!visible}
      /*
       * 셸(1200px = 75rem) 왼쪽 바깥에 세운다. 42.375rem = 셸 절반(37.5) + 바 폭(3.875) + 여백(1).
       * 50%-30rem 처럼 본문 기준으로 잡으면 1440px 에서 본문 위로 올라탄다.
       */
      className={`fixed left-[calc(50%-42.375rem)] top-1/2 z-30 hidden -translate-y-1/2 flex-col items-center gap-2 rounded-full border border-border bg-surface p-2 shadow-card transition-opacity duration-200 wide:flex ${
        visible ? 'opacity-100' : 'pointer-events-none opacity-0'
      }`}
    >
      <button
        type="button"
        onClick={onLike}
        disabled={busy}
        aria-pressed={liked}
        aria-label={liked ? '좋아요 취소' : '좋아요'}
        className={`grid h-11 w-11 place-items-center rounded-full border transition-colors disabled:opacity-60 ${
          liked
            ? 'border-accent-text bg-accent-text text-accent-contrast'
            : 'border-border text-ink-muted hover:border-ink-faint hover:text-ink'
        }`}
      >
        <HeartIcon className="h-5 w-5" filled={liked} />
      </button>
      <span className="text-sm font-bold tabular-nums text-ink-muted">{count}</span>

      <button
        type="button"
        onClick={onShare}
        aria-label="주소 공유"
        className="grid h-11 w-11 place-items-center rounded-full border border-border text-ink-muted transition-colors hover:border-ink-faint hover:text-ink"
      >
        <svg
          className="h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.75}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.5 1.5" />
          <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.5-1.5" />
        </svg>
      </button>
    </div>
  )
}
