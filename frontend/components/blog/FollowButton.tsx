'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { socialService } from '@/features/social/services/socialService'
import { useToastStore } from '@/store/toastStore'

/**
 * 팔로우 버튼.
 *
 * 부모 페이지는 서버 컴포넌트라 캐시된 응답을 쓴다. 캐시에는 "내가 팔로우 중인지"를
 * 담을 수 없으므로(사람마다 다르다) 마운트 후 클라이언트에서 채운다.
 */
export default function FollowButton({ handle }: { handle: string }) {
  const { data: session, status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [following, setFollowing] = useState<boolean | null>(null)
  const [busy, setBusy] = useState(false)

  const isMe = session?.user?.id ? false : false

  useEffect(() => {
    if (status !== 'authenticated') {
      setFollowing(null)
      return
    }
    // 공개 API 는 토큰이 있으면 is_following 을 채워준다.
    fetch(`/api/v1/public/blogs/${encodeURIComponent(handle)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setFollowing(data?.is_following ?? false))
      .catch(() => setFollowing(false))
  }, [handle, status])

  const onClick = async () => {
    if (status !== 'authenticated') {
      router.push('/auth/login')
      return
    }
    try {
      setBusy(true)
      const result = await socialService.toggleFollow(handle)
      setFollowing(result.following)
      // 팔로워 수는 서버에서 렌더된 값이라 갱신이 필요하다.
      router.refresh()
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '요청에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      aria-pressed={following ?? false}
      className={`inline-flex min-h-touch items-center rounded-full px-6 font-semibold transition-colors disabled:opacity-60 ${
        following
          ? 'border border-border bg-surface text-ink hover:bg-bg'
          : 'bg-ink text-bg'
      }`}
    >
      {following ? '팔로잉' : '팔로우'}
    </button>
  )
}
