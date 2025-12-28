'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { draftService, Draft } from '@/features/drafts/services/draftService'
import { safetyService, RiskFinding } from '@/features/safety/services/safetyService'
import { useToastStore } from '@/store/toastStore'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Link from 'next/link'

export default function DraftEditPage() {
  const params = useParams()
  const router = useRouter()
  const { data: session } = useSession()
  const { addToast } = useToastStore()
  const draftId = params.id as string

  const [draft, setDraft] = useState<Draft | null>(null)
  const [content, setContent] = useState('')
  const [activeTab, setActiveTab] = useState<'content' | 'safety' | 'export' | 'versions' | 'transform' | 'metadata' | 'compare'>('content')
  const [findings, setFindings] = useState<RiskFinding[]>([])
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [saving, setSaving] = useState(false)
  const [transforming, setTransforming] = useState(false)
  const [versions, setVersions] = useState<any[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [notes, setNotes] = useState('')
  const [checklist, setChecklist] = useState<Array<{id: string, text: string, checked: boolean}>>([])
  const [comparingVersions, setComparingVersions] = useState<{v1: string | null, v2: string | null}>({v1: null, v2: null})
  const [diffResult, setDiffResult] = useState<any>(null)
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!session) {
      router.push('/auth/login')
      return
    }
    loadDraft()
  }, [draftId, session, router])

  // 자동 저장 (debounce)
  useEffect(() => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current)
    }

    autoSaveTimerRef.current = setTimeout(() => {
      if (content && draft) {
        handleSave(true) // silent save
      }
    }, 2000) // 2초 후 자동 저장

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
      }
    }
  }, [content])

  const loadDraft = async () => {
    try {
      setLoading(true)
      const loadedDraft = await draftService.get(draftId)
      setDraft(loadedDraft)
      setContent(loadedDraft.latest_version?.content_md || '')
      // 메타데이터 로드
      if (loadedDraft.tags) setTags(loadedDraft.tags)
      if (loadedDraft.notes) setNotes(loadedDraft.notes)
      if (loadedDraft.checklist) setChecklist(loadedDraft.checklist)
      // 버전 목록도 로드
      const versionsData = await draftService.getVersions?.(draftId) || []
      setVersions(versionsData)
    } catch (err: any) {
      addToast({
        message: `Draft 로드 실패: ${err.message}`,
        type: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateMetadata = async () => {
    try {
      await draftService.update(draftId, {
        tags,
        notes,
        checklist,
      })
      addToast({
        message: '메타데이터가 저장되었습니다.',
        type: 'success',
      })
    } catch (err: any) {
      addToast({
        message: `저장 실패: ${err.message}`,
        type: 'error',
      })
    }
  }

  const handleCompareVersions = async () => {
    if (!comparingVersions.v1 || !comparingVersions.v2) {
      addToast({
        message: '비교할 두 버전을 선택해주세요.',
        type: 'error',
      })
      return
    }

    try {
      const result = await draftService.compareVersions(draftId, comparingVersions.v1, comparingVersions.v2)
      setDiffResult(result)
      setActiveTab('compare')
    } catch (err: any) {
      addToast({
        message: `비교 실패: ${err.message}`,
        type: 'error',
      })
    }
  }

  const handleSave = async (silent = false) => {
    try {
      setSaving(true)
      await draftService.updateVersion(draftId, {
        content_md: content,
        meta_json: draft?.latest_version?.meta_json || {},
      })
      if (!silent) {
        addToast({
          message: '저장되었습니다.',
          type: 'success',
        })
      }
      await loadDraft()
    } catch (err: any) {
      addToast({
        message: `저장 실패: ${err.message}`,
        type: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  const handleTransform = async (transformType: string) => {
    try {
      setTransforming(true)
      const result = await draftService.transform(draftId, {
        transform_type: transformType,
        user_id: session?.user?.id || '',
      })
      addToast({
        message: '변형이 시작되었습니다. 잠시 후 새 버전이 생성됩니다.',
        type: 'info',
      })
      // Job 상태 확인 후 새 버전 로드
      setTimeout(() => {
        loadDraft()
      }, 3000)
    } catch (err: any) {
      addToast({
        message: `변형 실패: ${err.message}`,
        type: 'error',
      })
    } finally {
      setTransforming(false)
    }
  }

  const handleScan = async () => {
    try {
      setScanning(true)
      const result = await safetyService.scan(draftId)
      setFindings(result.findings)
    } catch (err: any) {
      addToast({
        message: `Safety 검사 실패: ${err.message}`,
        type: 'error',
      })
    } finally {
      setScanning(false)
    }
  }

  const handleApplyFix = async (findingId: string, action: 'mask' | 'delete' | 'ignore') => {
    try {
      await safetyService.applyFix(draftId, { finding_id: findingId, action })
      await loadDraft()
      await handleScan()
      addToast({
        message: '적용되었습니다.',
        type: 'success',
      })
    } catch (err: any) {
      addToast({
        message: `적용 실패: ${err.message}`,
        type: 'error',
      })
    }
  }

  const handleCopyMarkdown = () => {
    navigator.clipboard.writeText(content)
    addToast({
      message: '마크다운이 클립보드에 복사되었습니다.',
      type: 'success',
    })
  }

  const handleDownloadMarkdown = async () => {
    try {
      const blob = await draftService.exportMarkdown(draftId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `draft-${draftId}.md`
      a.click()
      window.URL.revokeObjectURL(url)
      addToast({
        message: '다운로드되었습니다.',
        type: 'success',
      })
    } catch (err: any) {
      addToast({
        message: `다운로드 실패: ${err.message}`,
        type: 'error',
      })
    }
  }

  if (loading) {
    return (
      <div className="bg-[#f9f9f7] min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#d1fb52] mx-auto mb-4"></div>
          <p className="text-[#666666]">로딩 중...</p>
        </div>
      </div>
    )
  }

  if (!draft) {
    return (
      <div className="bg-[#f9f9f7] min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-[#666666] mb-4">Draft를 찾을 수 없습니다.</p>
          <Link href="/dashboard" className="text-[#666666] hover:text-[#111111] transition-colors">
            Dashboard로 돌아가기
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-[#f9f9f7] min-h-screen">
      <div className="max-w-[1400px] mx-auto px-[5%] py-12">
        <div className="mb-8 flex justify-between items-start">
          <div>
            <Link href="/dashboard" className="text-[#666666] hover:text-[#111111] mb-4 inline-block transition-colors">
              ← Dashboard로 돌아가기
            </Link>
            <h1 className="text-5xl font-bold text-[#111111] tracking-tight">Draft 편집</h1>
          </div>
          <button
            onClick={() => handleSave(false)}
            disabled={saving}
            className="px-6 py-3 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold disabled:bg-gray-300"
          >
            {saving ? '저장 중...' : '저장'}
          </button>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-[32px] border border-black/5 mb-8 overflow-hidden">
          <div className="flex border-b border-black/10 overflow-x-auto">
            <button
              onClick={() => setActiveTab('content')}
              className={`px-6 py-5 font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'content'
                  ? 'text-[#111111] border-b-2 border-[#d1fb52]'
                  : 'text-[#666666] hover:text-[#111111]'
              }`}
            >
              Content
            </button>
            <button
              onClick={() => setActiveTab('transform')}
              className={`px-6 py-5 font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'transform'
                  ? 'text-[#111111] border-b-2 border-[#d1fb52]'
                  : 'text-[#666666] hover:text-[#111111]'
              }`}
            >
              변형
            </button>
            <button
              onClick={() => setActiveTab('versions')}
              className={`px-6 py-5 font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'versions'
                  ? 'text-[#111111] border-b-2 border-[#d1fb52]'
                  : 'text-[#666666] hover:text-[#111111]'
              }`}
            >
              버전
            </button>
            <button
              onClick={() => setActiveTab('safety')}
              className={`px-6 py-5 font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'safety'
                  ? 'text-[#111111] border-b-2 border-[#d1fb52]'
                  : 'text-[#666666] hover:text-[#111111]'
              }`}
            >
              Safety
            </button>
            <button
              onClick={() => setActiveTab('metadata')}
              className={`px-6 py-5 font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'metadata'
                  ? 'text-[#111111] border-b-2 border-[#d1fb52]'
                  : 'text-[#666666] hover:text-[#111111]'
              }`}
            >
              메타데이터
            </button>
            <button
              onClick={() => setActiveTab('export')}
              className={`px-6 py-5 font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'export'
                  ? 'text-[#111111] border-b-2 border-[#d1fb52]'
                  : 'text-[#666666] hover:text-[#111111]'
              }`}
            >
              Export
            </button>
          </div>
        </div>

        {activeTab === 'content' && (
          <div className="grid lg:grid-cols-2 gap-8">
            <div className="bg-white rounded-[32px] border border-black/5 p-8">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-[#111111]">Markdown 에디터</h2>
                {saving && <span className="text-sm text-[#666666]">저장 중...</span>}
              </div>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full h-[600px] p-6 border border-black/10 rounded-2xl font-mono text-sm focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7] resize-none"
              />
            </div>
            <div className="bg-white rounded-[32px] border border-black/5 p-8">
              <h2 className="text-2xl font-bold mb-6 text-[#111111]">Preview</h2>
              <div className="w-full h-[600px] p-6 border border-black/10 rounded-2xl overflow-y-auto prose max-w-none bg-[#f9f9f7]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'transform' && (
          <div className="bg-white rounded-[32px] border border-black/5 p-8">
            <h2 className="text-2xl font-bold mb-6 text-[#111111]">변형 기능</h2>
            <p className="text-[#666666] mb-8">초안을 원하는 방향으로 변형할 수 있습니다.</p>
            <div className="grid md:grid-cols-2 gap-4">
              <button
                onClick={() => handleTransform('shorten')}
                disabled={transforming}
                className="p-6 bg-[#f9f9f7] rounded-2xl border border-black/10 hover:bg-[#d1fb52] hover:border-[#d1fb52] transition-colors disabled:opacity-50"
              >
                <h3 className="font-bold text-lg text-[#111111] mb-2">더 짧게</h3>
                <p className="text-sm text-[#666666]">내용을 간결하게 요약합니다.</p>
              </button>
              <button
                onClick={() => handleTransform('expand')}
                disabled={transforming}
                className="p-6 bg-[#f9f9f7] rounded-2xl border border-black/10 hover:bg-[#d1fb52] hover:border-[#d1fb52] transition-colors disabled:opacity-50"
              >
                <h3 className="font-bold text-lg text-[#111111] mb-2">더 길게</h3>
                <p className="text-sm text-[#666666]">내용을 더 자세하게 확장합니다.</p>
              </button>
              <button
                onClick={() => handleTransform('simplify')}
                disabled={transforming}
                className="p-6 bg-[#f9f9f7] rounded-2xl border border-black/10 hover:bg-[#d1fb52] hover:border-[#d1fb52] transition-colors disabled:opacity-50"
              >
                <h3 className="font-bold text-lg text-[#111111] mb-2">쉽게</h3>
                <p className="text-sm text-[#666666]">초보자도 이해하기 쉽게 작성합니다.</p>
              </button>
              <button
                onClick={() => handleTransform('deepen')}
                disabled={transforming}
                className="p-6 bg-[#f9f9f7] rounded-2xl border border-black/10 hover:bg-[#d1fb52] hover:border-[#d1fb52] transition-colors disabled:opacity-50"
              >
                <h3 className="font-bold text-lg text-[#111111] mb-2">더 딥하게</h3>
                <p className="text-sm text-[#666666]">더 전문적이고 깊이 있게 작성합니다.</p>
              </button>
            </div>
          </div>
        )}

        {activeTab === 'versions' && (
          <div className="bg-white rounded-[32px] border border-black/5 p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-[#111111]">버전 히스토리</h2>
              <button
                onClick={() => setActiveTab('compare')}
                className="px-6 py-3 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold"
              >
                버전 비교
              </button>
            </div>
            {versions.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-[#666666]">버전 히스토리가 없습니다.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {versions.map((version, index) => (
                  <div
                    key={version.id}
                    className="p-6 border border-black/10 rounded-2xl hover:bg-[#f9f9f7] transition-colors"
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="font-bold text-lg text-[#111111] mb-2">
                          버전 {version.version_no}
                        </h3>
                        <p className="text-sm text-[#666666]">
                          {new Date(version.created_at).toLocaleString('ko-KR')}
                        </p>
                      </div>
                      {index === 0 && (
                        <span className="px-4 py-2 bg-[#d1fb52] text-black rounded-full text-xs font-semibold">
                          최신
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => {
                        setContent(version.content_md)
                        setActiveTab('content')
                      }}
                      className="text-sm text-[#666666] hover:text-[#111111] transition-colors"
                    >
                      이 버전으로 복원 →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'safety' && (
          <div className="bg-white rounded-[32px] border border-black/5 p-8">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-2xl font-bold text-[#111111]">Safety 검사</h2>
              <button
                onClick={handleScan}
                disabled={scanning}
                className="px-8 py-4 bg-red-600 text-white rounded-full hover:scale-105 transition-transform font-semibold disabled:bg-gray-300"
              >
                {scanning ? '검사 중...' : '검사 실행'}
              </button>
            </div>

            {findings.length === 0 ? (
              <div className="p-12 bg-[#d1fb52]/20 border border-[#d1fb52]/30 rounded-2xl text-center">
                <svg className="w-16 h-16 text-[#d1fb52] mx-auto mb-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-black font-semibold text-lg">민감정보가 발견되지 않았습니다.</p>
                <p className="text-[#666666] text-sm mt-2">안전하게 발행할 수 있습니다.</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-2xl">
                  <p className="text-yellow-800 font-semibold">
                    ⚠️ {findings.length}개의 민감정보가 발견되었습니다.
                  </p>
                </div>
                {findings.map((finding) => (
                  <div key={finding.id} className="p-6 border border-black/10 rounded-2xl hover:bg-[#f9f9f7] transition-colors">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <div className="flex items-center gap-3 mb-3">
                          <span className={`px-4 py-2 rounded-full text-xs font-semibold ${
                            finding.severity === 'high' ? 'bg-red-100 text-red-700' :
                            finding.severity === 'med' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {finding.severity}
                          </span>
                          <span className="px-4 py-2 bg-gray-100 text-[#666666] rounded-full text-xs font-semibold">
                            {finding.category}
                          </span>
                        </div>
                        <p className="text-sm text-[#666666]">
                          {finding.location.line}번째 줄, {finding.location.column}번째 열
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApplyFix(finding.id, 'mask')}
                          className="px-5 py-2.5 bg-yellow-600 text-white rounded-full hover:scale-105 transition-transform text-sm font-semibold"
                        >
                          마스킹
                        </button>
                        <button
                          onClick={() => handleApplyFix(finding.id, 'delete')}
                          className="px-5 py-2.5 bg-red-600 text-white rounded-full hover:scale-105 transition-transform text-sm font-semibold"
                        >
                          삭제
                        </button>
                        <button
                          onClick={() => handleApplyFix(finding.id, 'ignore')}
                          className="px-5 py-2.5 bg-gray-600 text-white rounded-full hover:scale-105 transition-transform text-sm font-semibold"
                        >
                          무시
                        </button>
                      </div>
                    </div>
                    <pre className="text-sm bg-[#f9f9f7] p-4 rounded-2xl border border-black/10 font-mono overflow-x-auto">
                      {finding.snippet}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'metadata' && (
          <div className="bg-white rounded-[32px] border border-black/5 p-8">
            <h2 className="text-2xl font-bold mb-8 text-[#111111]">메타데이터</h2>
            <div className="space-y-8">
              {/* 태그 */}
              <div>
                <label className="block text-sm font-semibold text-[#111111] mb-3">태그</label>
                <div className="flex flex-wrap gap-2 mb-3">
                  {tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-4 py-2 bg-[#d1fb52] text-black rounded-full text-sm font-semibold flex items-center gap-2"
                    >
                      {tag}
                      <button
                        onClick={() => setTags(tags.filter((_, i) => i !== idx))}
                        className="hover:text-red-600"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="태그 입력 후 Enter"
                    className="flex-1 p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        const value = (e.target as HTMLInputElement).value.trim()
                        if (value && !tags.includes(value)) {
                          setTags([...tags, value])
                          ;(e.target as HTMLInputElement).value = ''
                        }
                      }
                    }}
                  />
                </div>
              </div>

              {/* 노트 */}
              <div>
                <label className="block text-sm font-semibold text-[#111111] mb-3">노트</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="메모나 리마인더를 입력하세요..."
                  className="w-full p-4 border border-black/10 rounded-2xl h-32 focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7] resize-none"
                />
              </div>

              {/* 체크리스트 */}
              <div>
                <label className="block text-sm font-semibold text-[#111111] mb-3">체크리스트</label>
                <div className="space-y-2 mb-3">
                  {checklist.map((item) => (
                    <label key={item.id} className="flex items-center gap-3 p-3 bg-[#f9f9f7] rounded-xl hover:bg-gray-100 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={item.checked}
                        onChange={(e) => {
                          setChecklist(checklist.map(i =>
                            i.id === item.id ? { ...i, checked: e.target.checked } : i
                          ))
                        }}
                        className="w-5 h-5 text-[#d1fb52] rounded focus:ring-[#d1fb52]"
                      />
                      <span className={`flex-1 ${item.checked ? 'line-through text-[#666666]' : 'text-[#111111]'}`}>
                        {item.text}
                      </span>
                      <button
                        onClick={() => setChecklist(checklist.filter(i => i.id !== item.id))}
                        className="text-red-600 hover:text-red-700"
                      >
                        삭제
                      </button>
                    </label>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="체크리스트 항목 추가"
                    className="flex-1 p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        const value = (e.target as HTMLInputElement).value.trim()
                        if (value) {
                          setChecklist([...checklist, {
                            id: Date.now().toString(),
                            text: value,
                            checked: false,
                          }])
                          ;(e.target as HTMLInputElement).value = ''
                        }
                      }
                    }}
                  />
                </div>
              </div>

              <button
                onClick={handleUpdateMetadata}
                className="w-full px-8 py-4 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold"
              >
                저장
              </button>
            </div>
          </div>
        )}

        {activeTab === 'compare' && (
          <div className="bg-white rounded-[32px] border border-black/5 p-8">
            <h2 className="text-2xl font-bold mb-8 text-[#111111]">버전 비교</h2>
            {!diffResult ? (
              <div className="space-y-6">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-[#111111] mb-3">버전 1</label>
                    <select
                      value={comparingVersions.v1 || ''}
                      onChange={(e) => setComparingVersions({...comparingVersions, v1: e.target.value})}
                      className="w-full p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                    >
                      <option value="">선택하세요</option>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>버전 {v.version_no}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-[#111111] mb-3">버전 2</label>
                    <select
                      value={comparingVersions.v2 || ''}
                      onChange={(e) => setComparingVersions({...comparingVersions, v2: e.target.value})}
                      className="w-full p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                    >
                      <option value="">선택하세요</option>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>버전 {v.version_no}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <button
                  onClick={handleCompareVersions}
                  disabled={!comparingVersions.v1 || !comparingVersions.v2}
                  className="w-full px-8 py-4 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  비교하기
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="grid md:grid-cols-2 gap-4 p-4 bg-[#f9f9f7] rounded-2xl">
                  <div>
                    <p className="text-sm text-[#666666] mb-1">버전 {diffResult.version1.version_no}</p>
                    <p className="font-semibold">단어: {diffResult.version1.word_count}</p>
                    <p className="font-semibold">줄: {diffResult.version1.line_count}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[#666666] mb-1">버전 {diffResult.version2.version_no}</p>
                    <p className="font-semibold">단어: {diffResult.version2.word_count}</p>
                    <p className="font-semibold">줄: {diffResult.version2.line_count}</p>
                  </div>
                </div>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="p-4 border border-black/10 rounded-2xl">
                    <h3 className="font-semibold mb-3">버전 {diffResult.version1.version_no}</h3>
                    <pre className="text-sm whitespace-pre-wrap bg-[#f9f9f7] p-4 rounded-xl max-h-96 overflow-auto">
                      {diffResult.version1.content}
                    </pre>
                  </div>
                  <div className="p-4 border border-black/10 rounded-2xl">
                    <h3 className="font-semibold mb-3">버전 {diffResult.version2.version_no}</h3>
                    <pre className="text-sm whitespace-pre-wrap bg-[#f9f9f7] p-4 rounded-xl max-h-96 overflow-auto">
                      {diffResult.version2.content}
                    </pre>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setDiffResult(null)
                    setComparingVersions({v1: null, v2: null})
                  }}
                  className="px-6 py-3 bg-gray-100 text-[#111111] rounded-full hover:bg-gray-200 transition-colors font-semibold"
                >
                  다시 비교
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'export' && (
          <div className="bg-white rounded-[32px] border border-black/5 p-8">
            <h2 className="text-2xl font-bold mb-8 text-[#111111]">Export</h2>
            <div className="space-y-4 max-w-md">
              <button
                onClick={handleCopyMarkdown}
                className="w-full px-8 py-5 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold text-lg"
              >
                📋 Copy Markdown
              </button>
              <button
                onClick={handleDownloadMarkdown}
                className="w-full px-8 py-5 bg-[#111111] text-white rounded-full hover:scale-105 transition-transform font-semibold text-lg"
              >
                ⬇️ Download .md
              </button>
              <div className="p-6 bg-[#f9f9f7] rounded-2xl border border-black/10">
                <p className="text-sm text-[#666666]">
                  마크다운 파일을 다운로드하거나 클립보드에 복사할 수 있습니다.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
