'use client'

import { useRef, useState } from 'react'
import { apiClient } from '@/lib/api/client'
import { useToastStore } from '@/store/toastStore'

interface Props {
  /** 업로드 후 받은 공개 URL */
  onUploaded: (url: string) => void
  endpoint?: '/api/v1/uploads/images' | '/api/v1/uploads/avatar'
  label?: string
  className?: string
  children?: React.ReactNode
}

const ACCEPT = 'image/png,image/jpeg,image/gif,image/webp'
const MAX_BYTES = 5 * 1024 * 1024

export default function ImageUploader({
  onUploaded,
  endpoint = '/api/v1/uploads/images',
  label = '이미지 업로드',
  className,
  children,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const { addToast } = useToastStore()
  const [busy, setBusy] = useState(false)

  const pick = async (file: File) => {
    // 서버도 검사하지만, 여기서 막으면 큰 파일을 올려보내고 거절당하는 낭비가 없다.
    if (file.size > MAX_BYTES) {
      addToast({ message: '파일이 너무 큽니다 (최대 5MB).', type: 'error' })
      return
    }

    const form = new FormData()
    form.append('file', file)

    try {
      setBusy(true)
      const result = await apiClient.postForm<{ url: string }>(endpoint, form)
      onUploaded(result.url)
      addToast({ message: '업로드했습니다.', type: 'success' })
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '업로드에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) void pick(file)
        }}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        className={
          className ??
          'inline-flex min-h-touch items-center rounded border border-border bg-surface px-4 text-sm font-medium text-ink transition-colors hover:bg-surface-2 disabled:opacity-50'
        }
      >
        {children ?? (busy ? '업로드 중...' : label)}
      </button>
    </>
  )
}
