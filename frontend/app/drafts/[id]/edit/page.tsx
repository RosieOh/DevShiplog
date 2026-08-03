'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { draftService, Draft, DraftVersion } from '@/features/drafts/services/draftService'
import { safetyService, RiskFinding } from '@/features/safety/services/safetyService'
import { useJobStatus } from '@/features/drafts/hooks/useJobStatus'
import { useToastStore } from '@/store/toastStore'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Link from 'next/link'

const AUTOSAVE_DELAY_MS = 2000

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback
}

export default function DraftEditPage() {
  const params = useParams()
  const router = useRouter()
  const { status: sessionStatus } = useSession()
  const { addToast } = useToastStore()
  const draftId = params.id as string

  const [draft, setDraft] = useState<Draft | null>(null)
  const [content, setContent] = useState('')
  const [activeTab, setActiveTab] = useState<'content' | 'safety' | 'export' | 'versions' | 'transform'>('content')
  const [findings, setFindings] = useState<RiskFinding[]>([])
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [saving, setSaving] = useState(false)
  const [snapshotting, setSnapshotting] = useState(false)
  const [transformJobId, setTransformJobId] = useState<string | null>(null)
  const [versions, setVersions] = useState<DraftVersion[]>([])
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null)
  // 서버에 저장된 최신 내용. 이 값과 같으면 자동저장을 건너뛴다.
  const savedContentRef = useRef<string>('')

  const { jobStatus: transformJob } = useJobStatus(transformJobId)

  const loadDraft = useCallback(async () => {
    try {
      const loadedDraft = await draftService.get(draftId)
      setDraft(loadedDraft)
      const loadedContent = loadedDraft.latest_version?.content_md || ''
      setContent(loadedContent)
      savedContentRef.current = loadedContent
      setVersions(await draftService.getVersions(draftId))
    } catch (err) {
      addToast({ message: errorMessage(err, 'Draft 를 불러오지 못했습니다.'), type: 'error' })
    }
  }, [draftId, addToast])

  useEffect(() => {
    if (sessionStatus === 'loading') return
    if (sessionStatus === 'unauthenticated') {
      router.push('/auth/login')
      return
    }
    void loadDraft().finally(() => setLoading(false))
  }, [sessionStatus, router, loadDraft])

  const saveContent = useCallback(
    async (silent: boolean) => {
      if (content === savedContentRef.current) {
        if (!silent) addToast({ message: '변경사항이 없습니다.', type: 'info' })
        return
      }
      try {
        setSaving(true)
        // 자동저장은 새 버전을 만들지 않고 최신 버전을 제자리에서 수정한다.
        await draftService.saveContent(draftId, {
          content_md: content,
          meta_json: draft?.latest_version?.meta_json ?? null,
        })
        savedContentRef.current = content
        setLastSavedAt(new Date())
        if (!silent) addToast({ message: '저장되었습니다.', type: 'success' })
      } catch (err) {
        addToast({ message: errorMessage(err, '저장에 실패했습니다.'), type: 'error' })
      } finally {
        setSaving(false)
      }
    },
    [content, draftId, draft, addToast]
  )

  // 자동 저장 (debounce)
  useEffect(() => {
    if (loading || !draft) return

    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current)
    autoSaveTimerRef.current = setTimeout(() => void saveContent(true), AUTOSAVE_DELAY_MS)

    return () => {
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current)
    }
  }, [content, loading, draft, saveContent])

  /** 되돌리기 지점을 남기는 명시적 버전 저장 */
  const handleCreateSnapshot = async () => {
    try {
      setSnapshotting(true)
      await saveContent(true)
      const version = await draftService.createVersion(draftId, {
        content_md: content,
        meta_json: draft?.latest_version?.meta_json ?? null,
      })
      addToast({ message: `버전 ${version.version_no} 으로 저장했습니다.`, type: 'success' })
      await loadDraft()
    } catch (err) {
      addToast({ message: errorMessage(err, '버전 저장에 실패했습니다.'), type: 'error' })
    } finally {
      setSnapshotting(false)
    }
  }

  const handleTransform = async (transformType: string) => {
    try {
      const result = await draftService.transform(draftId, { transform_type: transformType })
      setTransformJobId(result.job_id)
      addToast({ message: '변형을 시작했습니다. 완료되면 자동으로 반영됩니다.', type: 'info' })
    } catch (err) {
      addToast({ message: errorMessage(err, '변형에 실패했습니다.'), type: 'error' })
    }
  }

  // 변형 Job 이 끝나면 결과를 반영한다 (고정 3초 대기 대신 실제 상태를 본다).
  useEffect(() => {
    if (!transformJob) return
    if (transformJob.status === 'succeeded') {
      setTransformJobId(null)
      addToast({ message: '변형이 완료되었습니다.', type: 'success' })
      void loadDraft()
    } else if (transformJob.status === 'failed') {
      setTransformJobId(null)
      addToast({ message: transformJob.error_text || '변형에 실패했습니다.', type: 'error' })
    }
  }, [transformJob, loadDraft, addToast])

  const handleScan = useCallback(async () => {
    try {
      setScanning(true)
      const result = await safetyService.scan(draftId)
      setFindings(result.findings)
      if (result.count === 0) {
        addToast({ message: '민감정보가 발견되지 않았습니다.', type: 'success' })
      }
    } catch (err) {
      addToast({ message: errorMessage(err, 'Safety 검사에 실패했습니다.'), type: 'error' })
    } finally {
      setScanning(false)
    }
  }, [draftId, addToast])

  const handleApplyFix = async (findingId: string, action: 'mask' | 'delete' | 'ignore') => {
    try {
      // 편집 중인 내용이 서버에 반영돼 있어야 오프셋이 맞는다.
      await saveContent(true)
      const result = await safetyService.applyFix(draftId, { finding_id: findingId, action })
      await loadDraft()
      await handleScan()
      addToast({ message: result.message, type: 'success' })
    } catch (err) {
      addToast({ message: errorMessage(err, '적용에 실패했습니다.'), type: 'error' })
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
    } catch (err) {
      addToast({ message: errorMessage(err, '다운로드에 실패했습니다.'), type: 'error' })
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
          <div className="flex items-center gap-3">
            <span className="text-sm text-[#666666]">
              {saving
                ? '저장 중...'
                : lastSavedAt
                  ? `${lastSavedAt.toLocaleTimeString('ko-KR')} 자동저장됨`
                  : '자동저장 대기 중'}
            </span>
            <button
              onClick={() => void saveContent(false)}
              disabled={saving}
              className="px-6 py-3 bg-white border border-black/10 text-[#111111] rounded-full hover:bg-[#f9f9f7] transition-colors font-semibold disabled:opacity-50"
            >
              저장
            </button>
            <button
              onClick={handleCreateSnapshot}
              disabled={snapshotting}
              title="현재 내용을 되돌리기 지점으로 남깁니다"
              className="px-6 py-3 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold disabled:bg-gray-300"
            >
              {snapshotting ? '저장 중...' : '버전 남기기'}
            </button>
          </div>
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
                disabled={Boolean(transformJobId)}
                className="p-6 bg-[#f9f9f7] rounded-2xl border border-black/10 hover:bg-[#d1fb52] hover:border-[#d1fb52] transition-colors disabled:opacity-50"
              >
                <h3 className="font-bold text-lg text-[#111111] mb-2">더 짧게</h3>
                <p className="text-sm text-[#666666]">내용을 간결하게 요약합니다.</p>
              </button>
              <button
                onClick={() => handleTransform('expand')}
                disabled={Boolean(transformJobId)}
                className="p-6 bg-[#f9f9f7] rounded-2xl border border-black/10 hover:bg-[#d1fb52] hover:border-[#d1fb52] transition-colors disabled:opacity-50"
              >
                <h3 className="font-bold text-lg text-[#111111] mb-2">더 길게</h3>
                <p className="text-sm text-[#666666]">내용을 더 자세하게 확장합니다.</p>
              </button>
              <button
                onClick={() => handleTransform('simplify')}
                disabled={Boolean(transformJobId)}
                className="p-6 bg-[#f9f9f7] rounded-2xl border border-black/10 hover:bg-[#d1fb52] hover:border-[#d1fb52] transition-colors disabled:opacity-50"
              >
                <h3 className="font-bold text-lg text-[#111111] mb-2">쉽게</h3>
                <p className="text-sm text-[#666666]">초보자도 이해하기 쉽게 작성합니다.</p>
              </button>
              <button
                onClick={() => handleTransform('deepen')}
                disabled={Boolean(transformJobId)}
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
            <h2 className="text-2xl font-bold mb-6 text-[#111111]">버전 히스토리</h2>
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
                          {version.created_at
                            ? new Date(version.created_at).toLocaleString('ko-KR')
                            : '-'}
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
