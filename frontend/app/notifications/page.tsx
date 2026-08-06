'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import {
  socialService,
  NotificationItem,
} from '@/features/social/services/socialService'
import { formatDate } from '@/lib/api/public'
import { useToastStore } from '@/store/toastStore'

const LABEL: Record<NotificationItem['type'], string> = {
  comment: '님이 댓글을 남겼습니다',
  reply: '님이 답글을 남겼습니다',
  like: '님이 좋아요를 눌렀습니다',
  follow: '님이 팔로우했습니다',
  // 다른 알림과 무게가 다르다. 이건 "당신 글이 지금 안 됩니다" 라는 뜻이다.
  signal_broken: '님이 이 글대로 했는데 안 된다고 알렸습니다',
}

export default function NotificationsPage() {
  const { status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [items, setItems] = useState<NotificationItem[]>([])
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const box = await socialService.notifications()
      setItems(box.items)
      setUnread(box.unread_count)
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '알림을 불러오지 못했습니다.',
        type: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [addToast])

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }
    if (status === 'authenticated') void load()
  }, [status, router, load])

  const markAllRead = async () => {
    try {
      await socialService.markNotificationsRead()
      await load()
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '처리에 실패했습니다.',
        type: 'error',
      })
    }
  }

  return (
    <div className="bg-bg min-h-screen">
      <div className="mx-auto max-w-[680px] px-[5%] py-12">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
          <h1 className="text-4xl font-bold tracking-tight text-ink">
            알림 {unread > 0 && <span className="text-2xl text-accent-text">{unread}</span>}
          </h1>
          {unread > 0 && (
            <button
              type="button"
              onClick={markAllRead}
              className="inline-flex min-h-touch items-center rounded border border-border bg-surface px-5 text-sm font-semibold text-ink hover:bg-bg"
            >
              모두 읽음
            </button>
          )}
        </div>

        {loading ? (
          <p className="py-16 text-center text-ink-muted">불러오는 중...</p>
        ) : items.length === 0 ? (
          <p className="py-16 text-center text-ink-muted">아직 알림이 없습니다.</p>
        ) : (
          <ul className="divide-y divide-border-subtle">
            {items.map((n) => (
              <li
                key={n.id}
                className={`flex flex-wrap items-baseline gap-x-1.5 gap-y-1 px-2 py-5 ${
                  n.read ? '' : 'bg-accent/10'
                }`}
              >
                <Link
                  href={`/@${n.actor.handle}`}
                  className="font-semibold text-ink hover:underline underline-offset-2"
                >
                  {n.actor.display_name}
                </Link>
                <span className="text-ink-muted">{LABEL[n.type]}</span>
                {n.post && (
                  <Link
                    href={n.post.url}
                    className="w-full truncate text-sm text-ink-muted hover:text-ink"
                  >
                    “{n.post.title}”
                  </Link>
                )}
                <time className="ml-auto text-xs text-ink-muted" dateTime={n.created_at ?? undefined}>
                  {formatDate(n.created_at)}
                </time>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
