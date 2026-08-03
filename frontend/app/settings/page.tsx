'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { profileService, MyProfile } from '@/features/profile/services/profileService'
import { useToastStore } from '@/store/toastStore'

const HANDLE_DEBOUNCE_MS = 400

export default function SettingsPage() {
  const { status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()

  const [profile, setProfile] = useState<MyProfile | null>(null)
  const [handle, setHandle] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [bio, setBio] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [check, setCheck] = useState<{ available: boolean; reason: string | null } | null>(null)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }
    if (status !== 'authenticated') return

    profileService
      .me()
      .then((me) => {
        setProfile(me)
        setHandle(me.handle ?? '')
        setDisplayName(me.display_name ?? '')
        setBio(me.bio ?? '')
      })
      .catch((err) =>
        addToast({
          message: err instanceof Error ? err.message : '프로필을 불러오지 못했습니다.',
          type: 'error',
        })
      )
      .finally(() => setLoading(false))
  }, [status, router, addToast])

  // 입력 중에 사용 가능 여부를 알려준다. 저장 버튼을 눌러서야 아는 건 늦다.
  useEffect(() => {
    const trimmed = handle.trim()
    if (!trimmed || trimmed === profile?.handle) {
      setCheck(null)
      return
    }
    const timer = setTimeout(() => {
      profileService
        .checkHandle(trimmed)
        .then((r) => setCheck({ available: r.available, reason: r.reason }))
        .catch(() => setCheck(null))
    }, HANDLE_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [handle, profile?.handle])

  const save = async () => {
    try {
      setSaving(true)
      const result = await profileService.update({
        handle: handle.trim() || undefined,
        display_name: displayName.trim() || undefined,
        bio,
      })
      setProfile(result)
      addToast({
        message: result.handle_changed
          ? '저장했습니다. 아이디가 바뀌어 기존 글 주소도 함께 변경되었습니다.'
          : '저장했습니다.',
        type: result.handle_changed ? 'warning' : 'success',
      })
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '저장에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-canvas min-h-screen py-24 text-center text-ink-muted">불러오는 중...</div>
    )
  }

  return (
    <div className="bg-canvas min-h-screen">
      <div className="mx-auto max-w-[680px] px-[5%] py-12">
        <h1 className="text-4xl font-bold tracking-tight text-ink">블로그 설정</h1>

        {profile?.needs_handle && (
          <div className="mt-6 rounded-2xl border border-accent bg-accent/20 p-5">
            <p className="font-semibold text-ink">아이디를 먼저 정해주세요</p>
            <p className="mt-1 text-sm text-ink">
              블로그 주소가 <code className="font-mono">devshiplog.com/@아이디</code> 형태라, 아이디가
              없으면 글을 발행할 수 없습니다.
            </p>
          </div>
        )}

        <div className="mt-8 space-y-8 rounded-[32px] border border-black/5 bg-surface p-8">
          <div>
            <label htmlFor="handle" className="block text-sm font-semibold text-ink">
              블로그 아이디
            </label>
            <div className="mt-2 flex items-center gap-1">
              <span className="text-ink-muted">devshiplog.com/@</span>
              <input
                id="handle"
                value={handle}
                onChange={(e) => setHandle(e.target.value)}
                aria-describedby="handle-hint"
                placeholder="thoh"
                className="flex-1 rounded-2xl border border-black/10 bg-canvas p-3 font-mono"
              />
            </div>
            <p id="handle-hint" className="mt-2 text-sm text-ink-muted">
              영문 소문자·숫자로 시작하고 끝나며, 중간에 <code className="font-mono">-</code> 와{' '}
              <code className="font-mono">_</code> 를 쓸 수 있습니다 (3~30자).
            </p>
            {check && (
              <p
                className={`mt-2 text-sm font-medium ${
                  check.available ? 'text-accent-ink' : 'text-red-700'
                }`}
              >
                {check.available ? '사용할 수 있습니다.' : check.reason}
              </p>
            )}
            {profile?.handle && handle.trim() && handle.trim() !== profile.handle && (
              <p className="mt-2 text-sm font-medium text-amber-800">
                아이디를 바꾸면 이미 발행한 글 {profile.post_count}개의 주소가 전부 바뀝니다. 외부에
                공유한 링크와 검색 결과가 깨질 수 있습니다.
              </p>
            )}
          </div>

          <div>
            <label htmlFor="display-name" className="block text-sm font-semibold text-ink">
              표시 이름
            </label>
            <input
              id="display-name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              maxLength={60}
              className="mt-2 w-full rounded-2xl border border-black/10 bg-canvas p-3"
            />
          </div>

          <div>
            <label htmlFor="bio" className="block text-sm font-semibold text-ink">
              소개
            </label>
            <textarea
              id="bio"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              maxLength={300}
              rows={4}
              className="mt-2 w-full resize-none rounded-2xl border border-black/10 bg-canvas p-3"
            />
            <p className="mt-1 text-right text-xs text-ink-muted">{bio.length} / 300</p>
          </div>

          <div className="flex flex-wrap items-center gap-3 border-t border-black/10 pt-6">
            <button
              type="button"
              onClick={save}
              disabled={saving || (check !== null && !check.available)}
              className="inline-flex min-h-touch items-center rounded-full bg-accent px-8 font-semibold text-ink motion-safe:hover:scale-105 transition-transform disabled:bg-gray-300"
            >
              {saving ? '저장 중...' : '저장'}
            </button>
            {profile?.handle && (
              <Link
                href={`/@${profile.handle}`}
                className="inline-flex min-h-touch items-center text-sm text-ink-muted hover:text-ink"
              >
                내 블로그 보기 →
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
