'use client'

import { useEffect } from 'react'
import { useToastStore } from '@/store/toastStore'
import { AlertIcon, CheckCircleIcon, CloseIcon } from '@/components/ui/icons'

const TONE = {
  success: {
    box: 'bg-ink text-bg border-accent',
    Icon: CheckCircleIcon,
    label: '성공',
  },
  error: {
    box: 'bg-danger/10 text-danger border-danger/30',
    Icon: AlertIcon,
    label: '오류',
  },
  warning: {
    box: 'bg-amber-50 text-warning border-amber-200',
    Icon: AlertIcon,
    label: '경고',
  },
  info: {
    box: 'bg-surface text-ink border-border',
    Icon: CheckCircleIcon,
    label: '알림',
  },
} as const

export default function Toast() {
  const { toasts, removeToast } = useToastStore()

  useEffect(() => {
    // 이전 구현은 forEach 콜백에서 정리 함수를 return 해 아무 효과가 없었고,
    // 토스트가 추가될 때마다 기존 토스트의 타이머까지 다시 만들어졌다.
    const timers = toasts
      .filter((toast) => toast.autoClose)
      .map((toast) => setTimeout(() => removeToast(toast.id), toast.duration ?? 3000))

    return () => timers.forEach(clearTimeout)
  }, [toasts, removeToast])

  return (
    // 토스트가 저장·생성 결과를 알리는 유일한 채널이므로 스크린리더에도 전달되어야 한다.
    <div
      className="fixed top-20 right-4 left-4 sm:left-auto z-50 flex flex-col gap-2 sm:max-w-sm"
      aria-live="polite"
      aria-relevant="additions"
    >
      {toasts.map((toast) => {
        const tone = TONE[toast.type] ?? TONE.info
        const { Icon } = tone

        return (
          <div
            key={toast.id}
            // 오류는 즉시 읽어주도록 alert, 나머지는 흐름을 끊지 않는 status 로 둔다.
            role={toast.type === 'error' ? 'alert' : 'status'}
            className={`rounded border p-4 shadow-lg shadow-card ${tone.box}`}
          >
            <div className="flex items-start gap-3">
              <Icon className="w-5 h-5 mt-0.5" />
              <p className="flex-1 font-medium leading-snug">
                {/* 색으로만 구분되던 성공/오류를 텍스트로도 전달한다. */}
                <span className="sr-only">{tone.label}: </span>
                {toast.message}
              </p>
              <button
                type="button"
                onClick={() => removeToast(toast.id)}
                aria-label="알림 닫기"
                className="-m-2 grid h-touch w-touch place-items-center rounded-full opacity-70 transition-opacity hover:opacity-100"
              >
                <CloseIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
