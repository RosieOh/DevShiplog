'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { postService, DraftPublishState } from '@/features/posts/services/postService'
import { profileService, MyProfile } from '@/features/profile/services/profileService'
import { useToastStore } from '@/store/toastStore'
import { AlertIcon, CheckCircleIcon } from '@/components/ui/icons'
import { revalidateContent, tagsForPostUrl } from '@/lib/revalidate'

const MAX_TAGS = 10

export default function PublishPanel({ draftId }: { draftId: string }) {
  const { addToast } = useToastStore()
  const [profile, setProfile] = useState<MyProfile | null>(null)
  const [state, setState] = useState<DraftPublishState | null>(null)
  const [title, setTitle] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  // 민감정보 경고를 한 번 본 뒤에만 강행할 수 있게 한다.
  const [sensitiveWarned, setSensitiveWarned] = useState(false)

  useEffect(() => {
    Promise.all([profileService.me(), postService.forDraft(draftId)])
      .then(([me, published]) => {
        setProfile(me)
        setState(published)
        if (published.published) {
          setTitle(published.title ?? '')
          setTags(published.tags ?? [])
        }
      })
      .catch(() => undefined)
  }, [draftId])

  const addTag = () => {
    const value = tagInput.trim()
    if (!value || tags.length >= MAX_TAGS) return
    if (!tags.some((t) => t.toLowerCase() === value.toLowerCase())) {
      setTags([...tags, value])
    }
    setTagInput('')
  }

  const publish = async (allowSensitive: boolean) => {
    if (!title.trim()) {
      addToast({ message: '제목을 입력해주세요.', type: 'error' })
      return
    }
    try {
      setBusy(true)
      const result = await postService.publish({
        draft_id: draftId,
        title: title.trim(),
        tags,
        allow_sensitive: allowSensitive,
      })
      setState({ published: true, ...result })
      setSensitiveWarned(false)
      // 공개 페이지는 서버에서 캐시되므로 발행 사실을 Next 서버에 알려야 한다.
      await revalidateContent(tagsForPostUrl(result.url))
      addToast({
        message: result.created ? '발행했습니다.' : '수정 내용을 반영했습니다.',
        type: 'success',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : '발행에 실패했습니다.'
      if (message.includes('민감정보')) setSensitiveWarned(true)
      addToast({ message, type: 'error' })
    } finally {
      setBusy(false)
    }
  }

  const unpublish = async () => {
    if (!state?.id) return
    try {
      setBusy(true)
      await postService.unpublish(state.id)
      setState({ ...state, status: 'unlisted' })
      await revalidateContent(tagsForPostUrl(state.url))
      addToast({ message: '글을 내렸습니다. 주소는 유지됩니다.', type: 'success' })
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '처리에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setBusy(false)
    }
  }

  if (profile?.needs_handle) {
    return (
      <div className="rounded-lg border border-border-subtle bg-surface p-8">
        <h2 className="text-2xl font-bold text-ink">발행하려면 아이디가 필요합니다</h2>
        <p className="mt-3 text-ink-muted">
          블로그 주소가 <code className="font-mono">devshiplog.com/@아이디</code> 형태라, 아이디를
          먼저 정해야 글 주소를 만들 수 있습니다.
        </p>
        <Link
          href="/settings"
          className="mt-6 inline-flex min-h-touch items-center rounded bg-ink px-8 font-semibold text-bg transition-opacity hover:opacity-85"
        >
          아이디 정하러 가기
        </Link>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border-subtle bg-surface p-8">
      <h2 className="text-2xl font-bold text-ink">발행</h2>

      {state?.published && (
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded bg-accent/20 p-4 text-sm">
          <CheckCircleIcon className="h-5 w-5 text-accent-text" />
          <span className="text-ink">
            {state.status === 'published' ? '발행됨' : '내려둠'} ·{' '}
            {state.url && (
              <Link href={state.url} className="font-mono underline underline-offset-2">
                {state.url}
              </Link>
            )}
          </span>
        </div>
      )}

      <div className="mt-6 space-y-6">
        <div>
          <label htmlFor="publish-title" className="block text-sm font-semibold text-ink">
            제목
          </label>
          <input
            id="publish-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={300}
            placeholder="글 제목"
            className="mt-2 w-full rounded border border-border bg-bg p-4 text-lg"
          />
          <p className="mt-2 text-sm text-ink-muted">
            제목이 곧 주소가 됩니다. 발행 후 제목을 바꿔도 주소는 유지됩니다.
          </p>
        </div>

        <div>
          <label htmlFor="publish-tags" className="block text-sm font-semibold text-ink">
            태그
          </label>
          <input
            id="publish-tags"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault()
                addTag()
              }
            }}
            placeholder="Enter 로 추가 (최대 10개)"
            className="mt-2 w-full rounded border border-border bg-bg p-3"
          />
          {tags.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-2">
              {tags.map((tag) => (
                <li key={tag}>
                  <button
                    type="button"
                    onClick={() => setTags(tags.filter((t) => t !== tag))}
                    aria-label={`${tag} 태그 제거`}
                    className="inline-flex items-center gap-1.5 rounded-full border border-border bg-bg px-3 py-1.5 text-sm text-ink hover:border-ink-faint"
                  >
                    {tag}
                    <span aria-hidden="true" className="text-ink-muted">
                      ×
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {sensitiveWarned && (
          <div className="flex gap-3 rounded border border-warning/30 bg-warning/10 p-4">
            <AlertIcon className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
            <div className="text-sm text-warning">
              <p className="font-semibold">민감정보로 보이는 값이 있습니다.</p>
              <p className="mt-1">
                공개된 글은 되돌릴 수 없습니다. Safety 탭에서 처리하거나, 확인했다면 아래 버튼으로
                그대로 발행할 수 있습니다.
              </p>
              <button
                type="button"
                onClick={() => publish(true)}
                disabled={busy}
                className="mt-3 inline-flex min-h-touch items-center rounded border border-warning/40 bg-surface px-5 font-semibold text-warning"
              >
                확인했습니다, 그대로 발행
              </button>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-3 border-t border-border pt-6">
          <button
            type="button"
            onClick={() => publish(false)}
            disabled={busy}
            className="inline-flex min-h-touch items-center rounded bg-ink px-8 font-semibold text-bg transition-opacity hover:opacity-85 disabled:opacity-50"
          >
            {busy ? '처리 중...' : state?.published ? '수정 내용 반영' : '발행하기'}
          </button>
          {state?.published && state.status === 'published' && (
            <button
              type="button"
              onClick={unpublish}
              disabled={busy}
              className="inline-flex min-h-touch items-center rounded border border-border bg-surface px-6 font-semibold text-ink hover:bg-bg"
            >
              내리기
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
