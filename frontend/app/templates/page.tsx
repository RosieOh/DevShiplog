'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { templateService, Template } from '@/features/templates/services/templateService'
import { useToastStore } from '@/store/toastStore'
import Link from 'next/link'

export default function TemplatesPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const { addToast } = useToastStore()
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    type: 'implementation',
    audience: 'intermediate',
    length_preset: 'default',
    style_profile_id: '',
  })

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login')
      return
    }
    if (status === 'authenticated') {
      loadTemplates()
    }
  }, [status, router])

  const loadTemplates = async () => {
    try {
      setLoading(true)
      const data = await templateService.list()
      setTemplates(data)
    } catch (err: any) {
      addToast({
        message: `템플릿 로드 실패: ${err.message}`,
        type: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCreateTemplate = async () => {
    try {
      await templateService.create(newTemplate)
      addToast({
        message: '템플릿이 생성되었습니다.',
        type: 'success',
      })
      setShowCreateModal(false)
      setNewTemplate({
        name: '',
        type: 'implementation',
        audience: 'intermediate',
        length_preset: 'default',
        style_profile_id: '',
      })
      loadTemplates()
    } catch (err: any) {
      addToast({
        message: `템플릿 생성 실패: ${err.message}`,
        type: 'error',
      })
    }
  }

  const handleDeleteTemplate = async (id: string) => {
    if (!confirm('이 템플릿을 삭제하시겠습니까?')) return

    try {
      await templateService.delete(id)
      addToast({
        message: '템플릿이 삭제되었습니다.',
        type: 'success',
      })
      loadTemplates()
    } catch (err: any) {
      addToast({
        message: `템플릿 삭제 실패: ${err.message}`,
        type: 'error',
      })
    }
  }

  const handleUseTemplate = (template: Template) => {
    router.push(`/drafts/new?template=${template.id}`)
  }

  return (
    <div className="bg-[#f9f9f7] min-h-screen">
      <div className="max-w-[1400px] mx-auto px-[5%] py-12">
        <div className="flex justify-between items-center mb-12">
          <div>
            <Link href="/dashboard" className="text-[#666666] hover:text-[#111111] mb-4 inline-block transition-colors">
              ← Dashboard로 돌아가기
            </Link>
            <h1 className="text-5xl font-bold text-[#111111] tracking-tight">템플릿 관리</h1>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-8 py-4 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold"
          >
            + 새 템플릿
          </button>
        </div>

        {loading ? (
          <div className="text-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#d1fb52] mx-auto"></div>
          </div>
        ) : templates.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-[32px] border border-black/5">
            <p className="text-[#666666] mb-6 text-lg">템플릿이 없습니다</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-8 py-4 bg-[#d1fb52] text-black rounded-full font-semibold hover:scale-105 transition-transform"
            >
              첫 템플릿 만들기
            </button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map((template) => (
              <div
                key={template.id}
                className="bg-white rounded-[32px] border border-black/5 p-6 hover:-translate-y-2 transition-transform"
              >
                <h3 className="text-xl font-bold text-[#111111] mb-4">{template.name}</h3>
                <div className="space-y-2 mb-6 text-sm text-[#666666]">
                  <p>타입: {template.type}</p>
                  <p>대상: {template.audience}</p>
                  <p>길이: {template.length_preset}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleUseTemplate(template)}
                    className="flex-1 px-4 py-2 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold text-sm"
                  >
                    사용하기
                  </button>
                  <button
                    onClick={() => handleDeleteTemplate(template.id)}
                    className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-full transition-colors"
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 생성 모달 */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-[32px] p-8 max-w-md w-full">
              <h2 className="text-2xl font-bold mb-6 text-[#111111]">새 템플릿</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-[#111111] mb-2">이름</label>
                  <input
                    type="text"
                    value={newTemplate.name}
                    onChange={(e) => setNewTemplate({...newTemplate, name: e.target.value})}
                    className="w-full p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                    placeholder="템플릿 이름"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-[#111111] mb-2">타입</label>
                  <select
                    value={newTemplate.type}
                    onChange={(e) => setNewTemplate({...newTemplate, type: e.target.value})}
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
                  <label className="block text-sm font-semibold text-[#111111] mb-2">대상</label>
                  <select
                    value={newTemplate.audience}
                    onChange={(e) => setNewTemplate({...newTemplate, audience: e.target.value})}
                    className="w-full p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                  >
                    <option value="junior">주니어</option>
                    <option value="intermediate">중급</option>
                    <option value="interviewer">면접관</option>
                    <option value="team">팀원 공유</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-[#111111] mb-2">길이</label>
                  <select
                    value={newTemplate.length_preset}
                    onChange={(e) => setNewTemplate({...newTemplate, length_preset: e.target.value})}
                    className="w-full p-4 border border-black/10 rounded-2xl focus:ring-2 focus:ring-[#d1fb52] bg-[#f9f9f7]"
                  >
                    <option value="short">짧게</option>
                    <option value="default">기본</option>
                    <option value="long">길게</option>
                  </select>
                </div>
                <div className="flex gap-3 pt-4">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 px-6 py-3 bg-gray-100 text-[#111111] rounded-full hover:bg-gray-200 transition-colors font-semibold"
                  >
                    취소
                  </button>
                  <button
                    onClick={handleCreateTemplate}
                    disabled={!newTemplate.name}
                    className="flex-1 px-6 py-3 bg-[#d1fb52] text-black rounded-full hover:scale-105 transition-transform font-semibold disabled:bg-gray-300"
                  >
                    생성
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

