'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import type { CommentNode } from '@/lib/api/public'
import { formatDate } from '@/lib/api/public'
import { socialService } from '@/features/social/services/socialService'
import { useToastStore } from '@/store/toastStore'
import { revalidateContent } from '@/lib/revalidate'

interface Props {
  postId: string
  handle: string
  slug: string
  comments: CommentNode[]
  commentCount: number
}

const MAX_LEN = 1000

export default function CommentSection({ postId, handle, slug, comments, commentCount }: Props) {
  const { status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [body, setBody] = useState('')
  const [replyTo, setReplyTo] = useState<string | null>(null)
  const [replyBody, setReplyBody] = useState('')
  const [busy, setBusy] = useState(false)

  const requireLogin = () => {
    if (status !== 'authenticated') {
      router.push('/auth/login')
      return true
    }
    return false
  }

  const submit = async (text: string, parentId?: string) => {
    if (requireLogin()) return
    const trimmed = text.trim()
    if (!trimmed) {
      addToast({ message: '댓글 내용을 입력해주세요.', type: 'error' })
      return
    }
    try {
      setBusy(true)
      await socialService.addComment(postId, trimmed, parentId)
      // router.refresh() 는 RSC 를 다시 그리지만 fetch 데이터 캐시는 그대로다.
      await revalidateContent([`post:${handle}:${slug}`, 'feed'])
      setBody('')
      setReplyBody('')
      setReplyTo(null)
      // 서버에서 렌더된 목록이라 새로고침으로 반영한다.
      router.refresh()
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '댓글 등록에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setBusy(false)
    }
  }

  const remove = async (commentId: string) => {
    try {
      await socialService.deleteComment(commentId)
      await revalidateContent([`post:${handle}:${slug}`, 'feed'])
      router.refresh()
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '삭제에 실패했습니다.',
        type: 'error',
      })
    }
  }

  const renderComment = (comment: CommentNode, isReply = false) => (
    <li key={comment.id} className={isReply ? 'ml-6 border-l border-black/10 pl-5' : ''}>
      <div className="py-5">
        {comment.deleted ? (
          // 답글이 달린 댓글을 통째로 지우면 대화 흐름이 끊긴다. 자리를 남긴다.
          <p className="text-sm italic text-ink-muted">삭제된 댓글입니다.</p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
              <Link
                href={`/@${comment.author?.handle}`}
                className="font-semibold text-ink hover:underline underline-offset-2"
              >
                {comment.author?.display_name}
              </Link>
              <span className="text-ink-muted" aria-hidden="true">·</span>
              <time className="text-ink-muted" dateTime={comment.created_at ?? undefined}>
                {formatDate(comment.created_at)}
              </time>
            </div>
            <p className="mt-2 whitespace-pre-wrap leading-relaxed text-ink">{comment.body}</p>

            <div className="mt-2 flex gap-3 text-sm">
              {!isReply && (
                <button
                  type="button"
                  onClick={() => setReplyTo(replyTo === comment.id ? null : comment.id)}
                  className="text-ink-muted transition-colors hover:text-ink"
                >
                  답글
                </button>
              )}
              {comment.is_mine && (
                <button
                  type="button"
                  onClick={() => remove(comment.id)}
                  className="text-ink-muted transition-colors hover:text-red-700"
                >
                  삭제
                </button>
              )}
            </div>
          </>
        )}

        {replyTo === comment.id && (
          <div className="mt-4">
            <label htmlFor={`reply-${comment.id}`} className="sr-only">
              답글 내용
            </label>
            <textarea
              id={`reply-${comment.id}`}
              value={replyBody}
              onChange={(e) => setReplyBody(e.target.value)}
              maxLength={MAX_LEN}
              rows={3}
              placeholder="답글을 입력하세요"
              className="w-full rounded-2xl border border-black/10 bg-canvas p-4 text-sm"
            />
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={() => submit(replyBody, comment.id)}
                disabled={busy}
                className="inline-flex min-h-touch items-center rounded-full bg-accent px-5 text-sm font-semibold text-ink disabled:opacity-60"
              >
                등록
              </button>
              <button
                type="button"
                onClick={() => setReplyTo(null)}
                className="inline-flex min-h-touch items-center rounded-full px-4 text-sm text-ink-muted hover:text-ink"
              >
                취소
              </button>
            </div>
          </div>
        )}
      </div>

      {comment.replies.length > 0 && (
        <ul>{comment.replies.map((reply) => renderComment(reply, true))}</ul>
      )}
    </li>
  )

  return (
    <section className="mt-12 border-t border-black/10 pt-10" aria-labelledby="comments-heading">
      <h2 id="comments-heading" className="text-xl font-bold text-ink">
        댓글 {commentCount}
      </h2>

      <div className="mt-6">
        <label htmlFor="new-comment" className="sr-only">
          댓글 내용
        </label>
        <textarea
          id="new-comment"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={MAX_LEN}
          rows={4}
          placeholder={
            status === 'authenticated' ? '댓글을 입력하세요' : '댓글을 쓰려면 로그인이 필요합니다'
          }
          className="w-full rounded-2xl border border-black/10 bg-surface p-4"
        />
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs text-ink-muted">
            {body.length} / {MAX_LEN}
          </span>
          <button
            type="button"
            onClick={() => submit(body)}
            disabled={busy}
            className="inline-flex min-h-touch items-center rounded-full bg-accent px-6 font-semibold text-ink motion-safe:hover:scale-105 transition-transform disabled:opacity-60"
          >
            댓글 등록
          </button>
        </div>
      </div>

      {comments.length > 0 ? (
        <ul className="mt-8 divide-y divide-black/5">{comments.map((c) => renderComment(c))}</ul>
      ) : (
        <p className="mt-10 text-center text-ink-muted">첫 댓글을 남겨보세요.</p>
      )}
    </section>
  )
}
