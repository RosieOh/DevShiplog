import { useEffect, useState } from 'react'
import { apiClient, API_BASE_URL } from '@/lib/api/client'
import { socialService } from '@/features/social/services/socialService'

/**
 * 읽지 않은 알림 수를 서버가 밀어준다.
 *
 * 폴링을 대신한다. 알림은 대부분의 시간 동안 아무 일도 없는데, 그때도 주기적으로
 * 요청이 나가면 접속자 수에 비례해 그냥 버려지는 쿼리가 쌓인다.
 *
 * SSE 가 못 붙는 환경(구형 프록시, 회사망)이 있으므로 폴링을 완전히 버리지는 않는다.
 * 스트림이 열리면 폴링을 멈추고, 끊기면 다시 켠다.
 */
export function useUnreadNotifications(enabled: boolean): number {
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    if (!enabled) {
      setUnread(0)
      return
    }

    let closed = false
    let source: EventSource | null = null
    let pollTimer: ReturnType<typeof setInterval> | null = null

    const pollOnce = () =>
      socialService
        .notifications()
        .then((box) => !closed && setUnread(box.unread_count))
        .catch(() => undefined)

    const startPolling = () => {
      if (pollTimer || closed) return
      pollTimer = setInterval(pollOnce, 30_000)
    }

    const stopPolling = () => {
      if (pollTimer) clearInterval(pollTimer)
      pollTimer = null
    }

    // 첫 값은 즉시 채운다. 스트림은 "바뀔 때" 만 보내므로 초기값이 필요하다.
    void pollOnce()

    void apiClient.getAccessToken().then((token) => {
      if (closed || !token) {
        startPolling()
        return
      }
      // EventSource 는 커스텀 헤더를 못 붙인다. 토큰을 쿼리로 넘긴다.
      source = new EventSource(
        `${API_BASE_URL}/api/v1/social/notifications/stream?token=${encodeURIComponent(token)}`
      )
      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'unread') {
            stopPolling()
            setUnread(Number(data.count) || 0)
          }
        } catch {
          // 형식이 깨진 프레임은 무시한다. 다음 프레임이 곧 온다.
        }
      }
      source.onerror = () => {
        // 서버가 상한에서 끊으면 EventSource 가 알아서 재접속한다.
        // 그 사이(그리고 영영 못 붙는 환경에서)는 폴링이 받아준다.
        startPolling()
      }
    })

    return () => {
      closed = true
      stopPolling()
      source?.close()
    }
  }, [enabled])

  return unread
}
