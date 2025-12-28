'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { useDraftGeneration } from '@/features/drafts/hooks/useDraftGeneration'
import { useJobStatus } from '@/features/drafts/hooks/useJobStatus'
import { sourceService } from '@/features/sources/services/sourceService'
import { draftService, Draft } from '@/features/drafts/services/draftService'
import { useToastStore } from '@/store/toastStore'
import Link from 'next/link'

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
  const [draft, setDraft] = useState<Draft | null>(null)
  const [extracting, setExtracting] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [outline, setOutline] = useState<any>(null)
  const [generatingOutline, setGeneratingOutline] = useState(false)
  const [showOutlinePreview, setShowOutlinePreview] = useState(false)

  const { generateDraft, loading, error, draftId, jobId } = useDraftGeneration()
  const { jobStatus } = useJobStatus(jobId)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
    }
  }, [status, router])

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
        const validUrls = urls.filter(u => u.trim())
        if (validUrls.length === 0) {
          addToast({
            message: '최소 하나의 URL을 입력해주세요.',
            type: 'error',
          })
          return
        }
        sources = await sourceService.extractURLs({ urls: validUrls, user_id: session.user.id })
      } else {
        if (!text.trim()) {
          addToast({
            message: '텍스트를 입력해주세요.',
            type: 'error',
          })
          return
        }
        sources = await sourceService.extractText({ raw_text: text, user_id: session.user.id })
      }
      
      setSourceIds(sources.map(s => s.id))
      addToast({
        message: `${sources.length}개의 소스가 추출되었습니다.`,
        type: 'success',
      })
    } catch (err: any) {
      addToast({
        message: `소스 추출 실패: ${err.message}`,
        type: 'error',
      })
    } finally {
      setExtracting(false)
    }
  }

  const handleGenerateOutline = async () => {
    if (sourceIds.length === 0) {
      addToast({
        message: '먼저 소스를 추출해주세요.',
        type: 'error',
      })
      return
    }

    try {
      setGeneratingOutline(true)
      const result = await draftService.generateOutline({
        source_ids: sourceIds,
        type: draftType,
        audience,
        length,
      })
      setOutline(result.outline)
      setShowOutlinePreview(true)
      addToast({
        message: '목차가 생성되었습니다.',
        type: 'success',
      })
    } catch (err: any) {
      addToast({
        message: `목차 생성 실패: ${err.message}`,
        type: 'error',
      })
    } finally {
      setGeneratingOutline(false)
    }
  }

  const handleGenerateDraft = async () => {
    if (!session?.user?.id) {
      addToast({
        message: '로그인이 필요합니다.',
        type: 'error',
      })
      return
    }

    if (sourceIds.length === 0) {
      addToast({
        message: '먼저 소스를 추출해주세요.',
        type: 'error',
      })
      return
    }

    try {
      setStreamingContent('')
      await generateDraft({
        source_ids: sourceIds,
        type: draftType,
        audience,
        length,
        use_style_profile: useStyleProfile,
        style_profile_id: styleProfileId || undefined,
        user_id: session.user.id,
      })
    } catch (err) {
      // Error is handled in hook
    }
  }

  // 스트리밍 처리
  useEffect(() => {
    if (jobId && jobStatus?.status === 'running') {
      const eventSource = new EventSource(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/jobs/${jobId}/stream`
      )
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'chunk') {
          setStreamingContent(prev => prev + data.content)
        } else if (data.type === 'done') {
          eventSource.close()
          loadDraft()
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
      }

      return () => {
        eventSource.close()
      }
    }
  }, [jobId, jobStatus?.status])

  const loadDraft = async () => {
    if (!draftId) return
    
    try {
      const loadedDraft = await draftService.get(draftId)
      setDraft(loadedDraft)
      setStreamingContent('')
    } catch (err: any) {
      addToast({
        message: `Draft 로드 실패: ${err.message}`,
        type: 'error',
      })
    }
  }

  useEffect(() => {
    if (jobStatus?.status === 'succeeded' && draftId && !draft) {
      loadDraft()
    }
  }, [jobStatus?.status, draftId, draft])

  return (
    <div className="bg-[#f9f9f7] min-h-screen">
      <div className="max-w-[1400px] mx-auto px-[5%] py-12">
        <div className="mb-8">
          <Link href="/dashboard" className="text-[#666666] hover:text-[#111111] mb-4 inline-block transition-colors">
            ← Dashboard로 돌아가기
          </Link>
          <h1 className="text-5xl font-bold text-[#111111] tracking-tight">새 글 만들기</h1>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* 좌측: 입력 & 옵션 */}
          <div className="space-y-6">
            <div className="bg-white rounded-[32px] border border-black/5 p-8">
              <h2 className="text-2xl font-bold mb-6 text-[#111111]">소스 입력</h2>
              
              <div className="mb-6">
                <div className="flex gap-2 mb-6">
                  <button
                    onClick={() => setSourceType('url')}
                    className={`flex-1 px-4 py-3 rounded-full font-semibold transition-colors ${
                      sourceType === 'url' 
                        ? 'bg-[#d1fb52] text-black' 
                        : 'bg-gray-100 text-[#666666] hover:bg-gray-200'
                    }`}
                  >
                    URL
                  </button>
                  <button
                    onClick={() => setSourceType('text')}
                    className={`flex-1 px-4 py-3 rounded-full font-semibold transition-colors ${
                      sourceType === 'text' 
                        ? 'bg-[#d1fb52] text-black' 
                        : 'bg-gray-100 text-[#666666] hover:bg-gray-200'
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
                          type="text"
                          value={url}
                          onChange={(e) => handleUrlChange(index, e.target.value)}
                          placeholder="https://..."
                          className="flex-1 p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] focus:border-transparent bg-[#f9f9f7]"
                        />
                        {urls.length > 1 && (
                          <button
                            onClick={() => handleRemoveUrl(index)}
                            className="px-4 text-red-600 hover:bg-red-50 rounded-2xl transition-colors"
                          >
                            삭제
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      onClick={handleAddUrl}
                      className="text-[#666666] hover:text-[#111111] text-sm font-semibold transition-colors"
                    >
                      + URL 추가
                    </button>
                  </div>
                ) : (
                  <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="텍스트 또는 로그를 입력하세요..."
                    className="w-full p-4 border border-black/10 rounded-2xl h-40 focus:ring-2 focus:ring-[#d1fb52] focus:border-transparent bg-[#f9f9f7] resize-none"
                  />
                )}

                <button
                  onClick={handleExtractSources}
                  disabled={extracting}
                  className="w-full mt-6 px-6 py-4 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {extracting ? '추출 중...' : '소스 추출'}
                </button>
              </div>

              {sourceIds.length > 0 && (
                <div className="space-y-4">
                  <div className="p-4 bg-[#d1fb52]/20 border border-[#d1fb52]/30 rounded-2xl">
                    <p className="text-black font-semibold">
                      ✓ {sourceIds.length}개의 소스가 준비되었습니다.
                    </p>
                  </div>
                  <button
                    onClick={handleGenerateOutline}
                    disabled={generatingOutline}
                    className="w-full px-6 py-4 bg-white border-2 border-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    {generatingOutline ? '목차 생성 중...' : '📋 목차 미리보기'}
                  </button>
                </div>
              )}
            </div>

            {/* 목차 미리보기 */}
            {showOutlinePreview && outline && (
              <div className="bg-white rounded-[32px] border border-black/5 p-8">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold text-[#111111]">목차 미리보기</h2>
                  <button
                    onClick={() => setShowOutlinePreview(false)}
                    className="text-[#666666] hover:text-[#111111] transition-colors"
                  >
                    ✕
                  </button>
                </div>
                
                {(outline.title_candidates || outline.titleCandidates) && (outline.title_candidates || outline.titleCandidates).length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-sm font-semibold text-[#666666] mb-3">제목 후보</h3>
                    <div className="space-y-2">
                      {(outline.title_candidates || outline.titleCandidates).map((title: string, idx: number) => (
                        <div key={idx} className="p-3 bg-[#f9f9f7] rounded-xl border border-black/5">
                          {title}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {outline.toc && outline.toc.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-[#666666] mb-3">목차</h3>
                    <ol className="space-y-2 list-decimal list-inside">
                      {outline.toc.map((item: any, idx: number) => (
                        <li key={idx} className="p-3 bg-[#f9f9f7] rounded-xl border border-black/5">
                          {typeof item === 'string' ? item : item.heading || item}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                <button
                  onClick={handleGenerateDraft}
                  disabled={loading}
                  className="w-full mt-6 px-6 py-4 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {loading ? '초안 생성 중...' : '이 목차로 초안 생성'}
                </button>
              </div>
            )}

            <div className="bg-white rounded-[32px] border border-black/5 p-8">
              <h2 className="text-2xl font-bold mb-6 text-[#111111]">생성 옵션</h2>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-semibold text-[#111111] mb-3">생성 타입</label>
                  <select
                    value={draftType}
                    onChange={(e) => setDraftType(e.target.value)}
                    className="w-full p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                  >
                    <option value="troubleshooting">트러블슈팅</option>
                    <option value="implementation">구현기</option>
                    <option value="retrospective">회고</option>
                    <option value="tutorial">튜토리얼</option>
                    <option value="release">릴리즈노트</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-[#111111] mb-3">대상 독자</label>
                  <select
                    value={audience}
                    onChange={(e) => setAudience(e.target.value)}
                    className="w-full p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                  >
                    <option value="junior">주니어</option>
                    <option value="intermediate">중급</option>
                    <option value="interviewer">면접관</option>
                    <option value="team">팀원 공유</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-[#111111] mb-3">길이</label>
                  <select
                    value={length}
                    onChange={(e) => setLength(e.target.value)}
                    className="w-full p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                  >
                    <option value="short">짧게 (800자)</option>
                    <option value="default">기본 (1500~2500자)</option>
                    <option value="long">길게 (4000자+)</option>
                  </select>
                </div>

                <div className="pt-6 border-t border-black/10">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useStyleProfile}
                      onChange={(e) => setUseStyleProfile(e.target.checked)}
                      className="w-5 h-5 text-[#d1fb52] rounded focus:ring-[#d1fb52]"
                    />
                    <span className="font-semibold text-[#111111]">내 Style DNA 사용</span>
                  </label>
                  {useStyleProfile && (
                    <input
                      type="text"
                      value={styleProfileId}
                      onChange={(e) => setStyleProfileId(e.target.value)}
                      placeholder="Style Profile ID (선택사항)"
                      className="w-full mt-4 p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                    />
                  )}
                </div>
              </div>
            </div>

            <button
              onClick={handleGenerateDraft}
              disabled={loading || sourceIds.length === 0}
              className="w-full px-8 py-5 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold text-lg disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {loading ? '생성 중...' : '초안 생성하기'}
            </button>

            {error && (
              <div className="p-6 bg-red-50 border border-red-200 rounded-2xl">
                <p className="text-red-700 font-semibold">{error}</p>
              </div>
            )}
          </div>

          {/* 우측: 결과 */}
          <div className="space-y-6">
            {jobStatus && (
              <div className="bg-white rounded-[32px] border border-black/5 p-8">
                <h2 className="text-2xl font-bold mb-6 text-[#111111]">생성 상태</h2>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-[#666666]">상태</span>
                    <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                      jobStatus.status === 'succeeded' ? 'bg-[#d1fb52] text-black' :
                      jobStatus.status === 'failed' ? 'bg-red-100 text-red-700' :
                      jobStatus.status === 'running' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-[#666666]'
                    }`}>
                      {jobStatus.status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#666666]">진행률</span>
                    <span className="font-semibold text-[#111111]">{jobStatus.progress}%</span>
                  </div>
                  {jobStatus.status === 'running' && (
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-[#d1fb52] h-2 rounded-full transition-all"
                        style={{ width: `${jobStatus.progress}%` }}
                      ></div>
                    </div>
                  )}
                  
                  {/* 단계별 진행률 */}
                  {jobStatus.steps && (
                    <div className="mt-6 space-y-3">
                      <h3 className="text-sm font-semibold text-[#666666] mb-3">단계별 진행</h3>
                      {Object.entries(jobStatus.steps).map(([step, data]: [string, any]) => {
                        const stepNames: Record<string, string> = {
                          ingest: '소스 수집',
                          outline: '목차 생성',
                          draft: '본문 작성',
                          style: '스타일 적용',
                          safety: '안전 검사',
                          polish: '최종 정리',
                        }
                        const isActive = jobStatus.current_step === step
                        const isCompleted = data.status === 'completed'
                        const isSkipped = data.status === 'skipped'
                        
                        return (
                          <div
                            key={step}
                            className={`p-3 rounded-xl border transition-all ${
                              isActive
                                ? 'bg-[#d1fb52]/20 border-[#d1fb52]'
                                : isCompleted
                                ? 'bg-green-50 border-green-200'
                                : isSkipped
                                ? 'bg-gray-50 border-gray-200 opacity-60'
                                : 'bg-gray-50 border-gray-200'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-semibold text-[#111111]">
                                {stepNames[step] || step}
                              </span>
                              {isCompleted && <span className="text-green-600">✓</span>}
                              {isSkipped && <span className="text-gray-400">⊘</span>}
                              {isActive && <span className="text-[#d1fb52] animate-pulse">●</span>}
                            </div>
                            {isActive && (
                              <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                                <div
                                  className="bg-[#d1fb52] h-1.5 rounded-full transition-all"
                                  style={{ width: `${data.progress || 0}%` }}
                                ></div>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                  
                  {jobStatus.error_text && (
                    <div className="p-4 bg-red-50 border border-red-200 rounded-2xl">
                      <p className="text-red-700 text-sm">{jobStatus.error_text}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {(streamingContent || draft?.latest_version) && (
              <div className="bg-white rounded-[32px] border border-black/5 p-8">
                <h2 className="text-2xl font-bold mb-6 text-[#111111]">
                  {streamingContent ? '생성 중...' : '생성된 초안'}
                </h2>
                <div className="p-6 bg-[#f9f9f7] rounded-2xl border border-black/5 max-h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm text-[#111111] font-mono">
                    {streamingContent || draft?.latest_version?.content_md || ''}
                  </pre>
                </div>
                {draftId && !streamingContent && (
                  <Link
                    href={`/drafts/${draftId}/edit`}
                    className="mt-6 block w-full text-center px-6 py-4 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold"
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
