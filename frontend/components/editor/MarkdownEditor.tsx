'use client'

import { useCallback, useRef, useState } from 'react'
import { uploadService } from '@/features/uploads/services/uploadService'
import { useToastStore } from '@/store/toastStore'

interface Props {
  value: string
  /** setState 형태를 그대로 받는다. 업로드가 끝난 뒤 자리표시자만 바꿔치기하려면
   *  그 사이에 사용자가 친 글자를 잃지 않도록 함수형 갱신이 필요하다. */
  onChange: React.Dispatch<React.SetStateAction<string>>
  className?: string
  /** 미리보기 쪽과 스크롤을 맞추기 위해 스크롤 비율을 올려보낸다. */
  onScrollRatio?: (ratio: number) => void
}

const MAX_IMAGE_BYTES = 5 * 1024 * 1024

/**
 * 마크다운 입력창.
 *
 * 이미지는 붙여넣기·드래그로 바로 올라간다. 이게 없으면 이미지를 하나 넣을 때마다
 * 업로드 → 주소 복사 → 마크다운 직접 타이핑을 해야 하고, 글 쓰는 흐름이 그때마다 끊긴다.
 */
export default function MarkdownEditor({ value, onChange, className, onScrollRatio }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)
  const { addToast } = useToastStore()
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(0)

  /** 커서 자리(또는 선택 영역)를 text 로 갈아끼운다. */
  const replaceSelection = useCallback(
    (text: string, selectionStart?: number, selectionEnd?: number) => {
      const el = ref.current
      if (!el) return
      const start = selectionStart ?? el.selectionStart
      const end = selectionEnd ?? el.selectionEnd
      const next = value.slice(0, start) + text + value.slice(end)
      onChange(next)
      // React 가 값을 다시 그린 뒤에 커서를 옮겨야 한다.
      requestAnimationFrame(() => {
        el.focus()
        el.setSelectionRange(start + text.length, start + text.length)
      })
    },
    [value, onChange]
  )

  const uploadFiles = useCallback(
    async (files: File[]) => {
      const images = files.filter((f) => f.type.startsWith('image/'))
      if (images.length === 0) return

      const el = ref.current
      const start = el?.selectionStart ?? value.length
      const end = el?.selectionEnd ?? value.length

      /*
       * 업로드가 끝날 때까지 자리를 잡아 둔다. 그러지 않으면 업로드 중에 글을 계속 쓸 때
       * 이미지가 엉뚱한 위치에 꽂힌다. 자리표시자를 나중에 주소로 바꿔치기한다.
       */
      const placeholders = images.map((f, i) => `![업로드 중... ${f.name}](#uploading-${Date.now()}-${i})`)
      replaceSelection(placeholders.join('\n') + '\n', start, end)

      setUploading((n) => n + images.length)
      for (let i = 0; i < images.length; i++) {
        const file = images[i]
        const placeholder = placeholders[i]
        try {
          if (file.size > MAX_IMAGE_BYTES) {
            throw new Error(`${file.name} 이(가) 5MB 를 넘습니다.`)
          }
          const result = await uploadService.image(file)
          const alt = file.name.replace(/\.[^.]+$/, '')
          onChange((current) => current.replace(placeholder, `![${alt}](${result.url})`))
        } catch (err) {
          onChange((current) => current.replace(placeholder + '\n', '').replace(placeholder, ''))
          addToast({
            message: err instanceof Error ? err.message : '이미지 업로드에 실패했습니다.',
            type: 'error',
          })
        } finally {
          setUploading((n) => n - 1)
        }
      }
    },
    [value, replaceSelection, onChange, addToast]
  )

  const onPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const files = Array.from(e.clipboardData.files)
    if (files.some((f) => f.type.startsWith('image/'))) {
      // 스크린샷 붙여넣기. 기본 동작(파일명만 삽입)을 막는다.
      e.preventDefault()
      void uploadFiles(files)
    }
  }

  const onDrop = (e: React.DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault()
    setDragging(false)
    void uploadFiles(Array.from(e.dataTransfer.files))
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Tab 이 포커스를 옮겨 버리면 코드 블록을 들여쓸 수 없다.
    if (e.key === 'Tab') {
      e.preventDefault()
      replaceSelection('  ')
      return
    }
    // 굵게 / 기울임 — 에디터에서 기대하는 최소한의 단축키
    const meta = e.metaKey || e.ctrlKey
    if (meta && (e.key === 'b' || e.key === 'i')) {
      e.preventDefault()
      const el = ref.current
      if (!el) return
      const marker = e.key === 'b' ? '**' : '_'
      const selected = value.slice(el.selectionStart, el.selectionEnd)
      replaceSelection(`${marker}${selected}${marker}`)
    }
  }

  return (
    <div className="relative flex h-full flex-col">
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onPaste={onPaste}
        onDrop={onDrop}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onKeyDown={onKeyDown}
        onScroll={(e) => {
          const el = e.currentTarget
          const scrollable = el.scrollHeight - el.clientHeight
          if (scrollable > 0) onScrollRatio?.(el.scrollTop / scrollable)
        }}
        spellCheck={false}
        aria-label="마크다운 편집기"
        className={`h-full w-full resize-none rounded border bg-bg p-6 font-mono text-sm leading-relaxed text-ink transition-colors ${
          dragging ? 'border-accent-text border-dashed' : 'border-border'
        } ${className ?? ''}`}
      />

      {dragging && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 grid place-items-center rounded bg-bg/80"
        >
          <p className="text-sm font-bold text-ink">놓으면 이미지가 업로드됩니다</p>
        </div>
      )}

      {/* 진행 상황은 조용히, 그러나 보이게. 업로드가 도는지 모르면 사용자는 다시 시도한다. */}
      <p className="mt-2 text-xs text-ink-faint" role="status" aria-live="polite">
        {uploading > 0
          ? `이미지 ${uploading}개 업로드 중...`
          : '이미지는 붙여넣거나 끌어다 놓으면 바로 올라갑니다.'}
      </p>
    </div>
  )
}
