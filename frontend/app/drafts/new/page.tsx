'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { useDraftGeneration } from '@/features/drafts/hooks/useDraftGeneration'
import { useJobStatus } from '@/features/drafts/hooks/useJobStatus'
import { sourceService } from '@/features/sources/services/sourceService'
import { draftService, Draft } from '@/features/drafts/services/draftService'
import {
  styleProfileService,
  StyleProfileResponse,
} from '@/features/style-profiles/services/styleProfileService'
import { apiClient } from '@/lib/api/client'
import { useToastStore } from '@/store/toastStore'
import Link from 'next/link'
import { CheckCircleIcon } from '@/components/ui/icons'

export default function NewDraftPage() {
  const router = useRouter()
  const { data: session, status } = useSession()
  const { addToast } = useToastStore()
  const [sourceType, setSourceType] = useState<'url' | 'text'>('url')
  const [urls, setUrls] = useState<string[]>([''])
  const [text, setText] = useState('')
  const [sourceIds, setSourceIds] = useState<string[]>([])
  const [draftType, setDraftType] = useState('implementation')
  const [audience, setAudience] = useState('intermediate')
  const [length, setLength] = useState('default')
  const [useStyleProfile, setUseStyleProfile] = useState(false)
  const [styleProfileId, setStyleProfileId] = useState('')
  const [styleProfiles, setStyleProfiles] = useState<StyleProfileResponse[]>([])
  const [draft, setDraft] = useState<Draft | null>(null)
  const [extracting, setExtracting] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')

  const { generateDraft, loading, error, draftId, jobId } = useDraftGeneration()
  const { jobStatus } = useJobStatus(jobId)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
    }
  }, [status, router])

  // 완성된 Style DNA 만 선택지로 보여준다.
  useEffect(() => {
    if (status !== 'authenticated') return
    styleProfileService
      .list()
      .then((profiles) => setStyleProfiles(profiles.filter((p) => p.status === 'succeeded')))
      .catch(() => setStyleProfiles([]))
  }, [status])

  const handleAddUrl = () => {
    setUrls([...urls, ''])
  }

  const handleUrlChange = (index: number, value: string) => {
    const newUrls = [...urls]
    newUrls[index] = value
    setUrls(newUrls)
  }

  const handleRemoveUrl = (index: number) => {
    const newUrls = urls.filter((_, i) => i !== index)
    setUrls(newUrls.length > 0 ? newUrls : [''])
  }

  const handleExtractSources = async () => {
    if (!session?.user?.id) {
      addToast({
        message: '로그인이 필요합니다.',
        type: 'error',
      })
      return
    }

    try {
      setExtracting(true)

      let sources
      if (sourceType === 'url') {
        const validUrls = urls.filter((u) => u.trim())
        if (validUrls.length === 0) {
          addToast({ message: '최소 하나의 URL을 입력해주세요.', type: 'error' })
          return
        }
        sources = await sourceService.extractURLs(validUrls)
      } else {
        if (!text.trim()) {
          addToast({ message: '텍스트를 입력해주세요.', type: 'error' })
          return
        }
        sources = await sourceService.extractText(text)
      }

      // 추출에 실패한 항목은 id 가 없다. 성공한 것만 사용하고 실패는 따로 알린다.
      const succeeded = sources.filter((s): s is typeof s & { id: string } => Boolean(s.id))
      const failed = sources.filter((s) => !s.id)

      setSourceIds(succeeded.map((s) => s.id))

      if (succeeded.length > 0) {
        addToast({
          message: `${succeeded.length}개의 소스가 추출되었습니다.`,
          type: 'success',
        })
      }
      failed.forEach((s) => {
        addToast({ message: `추출 실패 (${s.title}): ${s.error ?? '알 수 없는 오류'}`, type: 'error' })
      })
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : '소스 추출에 실패했습니다.',
        type: 'error',
      })
    } finally {
      setExtracting(false)
    }
  }

  const handleGenerateDraft = async () => {
    if (sourceIds.length === 0) {
      addToast({ message: '먼저 소스를 추출해주세요.', type: 'error' })
      return
    }

    try {
      setStreamingContent('')
      setDraft(null)
      await generateDraft({
        source_ids: sourceIds,
        type: draftType,
        audience,
        length,
        use_style_profile: useStyleProfile,
        style_profile_id: useStyleProfile ? styleProfileId || undefined : undefined,
      })
    } catch {
      // 오류 메시지는 훅의 error 상태로 표시된다.
    }
  }

  const loadDraft = useCallback(async () => {
    if (!draftId) return
    try {
      const loadedDraft = await draftService.get(draftId)
      setDraft(loadedDraft)
      setStreamingContent('')
    } catch (err) {
      addToast({
        message: err instanceof Error ? err.message : 'Draft 를 불러오지 못했습니다.',
        type: 'error',
      })
    }
  }, [draftId, addToast])

  // 실시간 스트리밍. Job 생성 직후 바로 연결한다.
  // (running 상태를 기다리면 짧은 작업에서 스트림을 통째로 놓칠 수 있다.)
  useEffect(() => {
    if (!jobId) return

    let eventSource: EventSource | null = null
    let closed = false

    const connect = async () => {
      // EventSource 는 헤더를 못 붙이므로 토큰을 쿼리로 넘긴다.
      const source = await apiClient.createEventSource(`/api/v1/jobs/${jobId}/stream`)
      if (closed) {
        source.close()
        return
      }
      eventSource = source

      source.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'chunk') {
          setStreamingContent((prev) => prev + data.content)
        } else if (data.type === 'done') {
          source.close()
          void loadDraft()
        } else if (data.type === 'error') {
          source.close()
          addToast({ message: data.message ?? '생성에 실패했습니다.', type: 'error' })
        }
      }

      // 네트워크 오류 시 EventSource 가 자동 재연결하며 무한 루프가 될 수 있어 닫는다.
      // 최종 상태는 useJobStatus 폴링이 확인해 준다.
      source.onerror = () => source.close()
    }

    void connect()

    return () => {
      closed = true
      eventSource?.close()
    }
  }, [jobId, loadDraft, addToast])

  // 스트림을 놓쳤더라도 폴링으로 완료를 감지하면 결과를 불러온다.
  useEffect(() => {
    if (jobStatus?.status === 'succeeded' && draftId && !draft) {
      void loadDraft()
    }
  }, [jobStatus?.status, draftId, draft, loadDraft])

  return (
    <div className="bg-bg min-h-screen">
      <div className="max-w-[1400px] mx-auto px-[5%] py-12">
        <div className="mb-8">
          <Link href="/dashboard" className="text-ink-muted hover:text-ink mb-4 inline-block transition-colors">
            ← Dashboard로 돌아가기
          </Link>
          <h1 className="text-5xl font-bold text-ink tracking-tight">새 글 만들기</h1>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* 좌측: 입력 & 옵션 */}
          <div className="space-y-6">
            <div className="bg-surface rounded-lg border border-border-subtle p-8">
              <h2 className="text-2xl font-bold mb-6 text-ink">소스 입력</h2>
              
              <div className="mb-6">
                <div className="flex gap-2 mb-6">
                  <button
                    onClick={() => setSourceType('url')}
                    className={`flex-1 px-4 py-3 rounded-full font-semibold transition-colors ${
                      sourceType === 'url' 
                        ? 'bg-ink text-bg' 
                        : 'bg-surface-2 text-ink-muted hover:bg-gray-200'
                    }`}
                  >
                    URL
                  </button>
                  <button
                    onClick={() => setSourceType('text')}
                    className={`flex-1 px-4 py-3 rounded-full font-semibold transition-colors ${
                      sourceType === 'text' 
                        ? 'bg-ink text-bg' 
                        : 'bg-surface-2 text-ink-muted hover:bg-gray-200'
                    }`}
                  >
                    텍스트/로그
                  </button>
                </div>

                {sourceType === 'url' ? (
                  <div className="space-y-3">
                    {urls.map((url, index) => (
                      <div key={index} className="flex gap-2">
                        <input
                          type="url"
                          inputMode="url"
                          aria-label={`소스 URL ${index + 1}`}
                          value={url}
                          onChange={(e) => handleUrlChange(index, e.target.value)}
                          placeholder="https://..."
                          className="flex-1 p-4 border border-border rounded bg-bg"
                        />
                        {urls.length > 1 && (
                          <button
                            type="button"
                            onClick={() => handleRemoveUrl(index)}
                            aria-label={`소스 URL ${index + 1} 삭제`}
                            className="px-4 min-h-touch text-danger hover:bg-danger/10 rounded transition-colors"
                          >
                            삭제
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      onClick={handleAddUrl}
                      className="text-ink-muted hover:text-ink text-sm font-semibold transition-colors"
                    >
                      + URL 추가
                    </button>
                  </div>
                ) : (
                  <textarea
                    id="raw-text"
                    aria-label="붙여넣을 텍스트 또는 로그"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="텍스트 또는 로그를 입력하세요..."
                    className="w-full p-4 border border-border rounded h-40 bg-bg resize-none font-mono text-sm"
                  />
                )}

                <button
                  onClick={handleExtractSources}
                  disabled={extracting}
                  className="w-full mt-6 px-6 py-4 bg-ink text-bg rounded-full transition-opacity hover:opacity-85 font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {extracting ? '추출 중...' : '소스 추출'}
                </button>
              </div>

              {sourceIds.length > 0 && (
                <div className="p-4 bg-accent/20 border border-accent/30 rounded">
                  <p className="flex items-center gap-2 text-ink font-semibold">
                    <CheckCircleIcon className="w-5 h-5" />
                    {sourceIds.length}개의 소스가 준비되었습니다.
                  </p>
                </div>
              )}
            </div>

            <div className="bg-surface rounded-lg border border-border-subtle p-8">
              <h2 className="text-2xl font-bold mb-6 text-ink">생성 옵션</h2>
              
              <div className="space-y-6">
                <div>
                  <label htmlFor="draft-type" className="block text-sm font-semibold text-ink mb-3">생성 타입</label>
                  <select
                    id="draft-type"
                    value={draftType}
                    onChange={(e) => setDraftType(e.target.value)}
                    className="w-full p-4 border border-border rounded bg-bg"
                  >
                    <option value="troubleshooting">트러블슈팅</option>
                    <option value="implementation">구현기</option>
                    <option value="retrospective">회고</option>
                    <option value="tutorial">튜토리얼</option>
                    <option value="release">릴리즈노트</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="draft-audience" className="block text-sm font-semibold text-ink mb-3">대상 독자</label>
                  <select
                    id="draft-audience"
                    value={audience}
                    onChange={(e) => setAudience(e.target.value)}
                    className="w-full p-4 border border-border rounded bg-bg"
                  >
                    <option value="junior">주니어</option>
                    <option value="intermediate">중급</option>
                    <option value="interviewer">면접관</option>
                    <option value="team">팀원 공유</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="draft-length" className="block text-sm font-semibold text-ink mb-3">길이</label>
                  <select
                    id="draft-length"
                    value={length}
                    onChange={(e) => setLength(e.target.value)}
                    className="w-full p-4 border border-border rounded bg-bg"
                  >
                    <option value="short">짧게 (800자)</option>
                    <option value="default">기본 (1500~2500자)</option>
                    <option value="long">길게 (4000자+)</option>
                  </select>
                </div>

                <div className="pt-6 border-t border-border">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useStyleProfile}
                      onChange={(e) => setUseStyleProfile(e.target.checked)}
                      className="w-5 h-5 rounded accent-accent"
                    />
                    <span className="font-semibold text-ink">내 Style DNA 사용</span>
                  </label>
                  {useStyleProfile &&
                    (styleProfiles.length > 0 ? (
                      <select
                        value={styleProfileId}
                        onChange={(e) => setStyleProfileId(e.target.value)}
                        className="w-full mt-4 p-4 border border-border rounded bg-bg"
                      >
                        <option value="">스타일 없이 생성</option>
                        {styleProfiles.map((profile) => (
                          <option key={profile.id} value={profile.id}>
                            {profile.blog_url}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <p className="mt-4 text-sm text-ink-muted">
                        아직 완성된 Style DNA가 없습니다.{' '}
                        <Link href="/onboarding/style" className="underline hover:text-ink">
                          Style DNA 만들기 →
                        </Link>
                      </p>
                    ))}
                </div>
              </div>
            </div>

            <button
              onClick={handleGenerateDraft}
              disabled={loading || sourceIds.length === 0}
              className="w-full px-8 py-5 bg-ink text-bg rounded-full transition-opacity hover:opacity-85 font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '생성 중...' : '초안 생성하기'}
            </button>

            {error && (
              <div className="p-6 bg-danger/10 border border-danger/30 rounded">
                <p className="text-danger font-semibold">{error}</p>
              </div>
            )}
          </div>

          {/* 우측: 결과 */}
          <div className="space-y-6">
            {jobStatus && (
              <div className="bg-surface rounded-lg border border-border-subtle p-8">
                <h2 className="text-2xl font-bold mb-6 text-ink">생성 상태</h2>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-ink-muted">상태</span>
                    <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                      jobStatus.status === 'succeeded' ? 'bg-ink text-bg' :
                      jobStatus.status === 'failed' ? 'bg-danger/15 text-danger' :
                      jobStatus.status === 'running' ? 'bg-accent/15 text-accent-text' :
                      'bg-surface-2 text-ink-muted'
                    }`}>
                      {jobStatus.status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-ink-muted">진행률</span>
                    <span className="font-semibold text-ink">{jobStatus.progress}%</span>
                  </div>
                  {jobStatus.status === 'running' && (
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-accent h-2 rounded-full transition-all"
                        style={{ width: `${jobStatus.progress}%` }}
                      ></div>
                    </div>
                  )}
                  {jobStatus.error_text && (
                    <div className="p-4 bg-danger/10 border border-danger/30 rounded">
                      <p className="text-danger text-sm">{jobStatus.error_text}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {(streamingContent || draft?.latest_version) && (
              <div className="bg-surface rounded-lg border border-border-subtle p-8">
                <h2 className="text-2xl font-bold mb-6 text-ink">
                  {streamingContent ? '생성 중...' : '생성된 초안'}
                </h2>
                <div className="p-6 bg-bg rounded border border-border-subtle max-h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm text-ink font-mono">
                    {streamingContent || draft?.latest_version?.content_md || ''}
                  </pre>
                </div>
                {draftId && !streamingContent && (
                  <Link
                    href={`/drafts/${draftId}/edit`}
                    className="mt-6 block w-full text-center px-6 py-4 bg-ink text-bg rounded-full transition-opacity hover:opacity-85 font-semibold"
                  >
                    에디터에서 열기 →
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
