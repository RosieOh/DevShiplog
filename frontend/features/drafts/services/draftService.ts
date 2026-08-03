import { apiClient } from '@/lib/api/client'

export interface CreateDraftRequest {
  source_ids: string[]
  type: string
  audience: string
  length: string
  use_style_profile: boolean
  style_profile_id?: string
}

export interface DraftJobResponse {
  id: string
  job_id: string
  status: string
}

export interface DraftVersion {
  id: string
  version_no: number
  content_md: string
  meta_json: Record<string, unknown> | null
  created_at: string | null
  updated_at: string | null
}

export interface Draft {
  id: string
  status: string
  type: string
  audience: string
  length_preset: string
  created_at: string | null
  latest_version: DraftVersion | null
}

export interface TransformDraftRequest {
  transform_type: string
}

export interface SaveContentRequest {
  content_md: string
  meta_json?: Record<string, unknown> | null
}

export const draftService = {
  create: async (data: CreateDraftRequest): Promise<DraftJobResponse> => {
    return apiClient.post('/api/v1/drafts', data)
  },

  get: async (draftId: string): Promise<Draft> => {
    return apiClient.get(`/api/v1/drafts/${draftId}`)
  },

  list: async (): Promise<Draft[]> => {
    return apiClient.get('/api/v1/drafts')
  },

  /** 자동저장 — 최신 버전을 제자리에서 수정한다 (버전이 늘어나지 않음) */
  saveContent: async (draftId: string, data: SaveContentRequest): Promise<DraftVersion> => {
    return apiClient.put(`/api/v1/drafts/${draftId}/content`, data)
  },

  /** 명시적 스냅샷 — 되돌리기 지점을 남긴다 */
  createVersion: async (draftId: string, data: SaveContentRequest): Promise<DraftVersion> => {
    return apiClient.post(`/api/v1/drafts/${draftId}/versions`, data)
  },

  getVersions: async (draftId: string): Promise<DraftVersion[]> => {
    return apiClient.get(`/api/v1/drafts/${draftId}/versions`)
  },

  transform: async (draftId: string, data: TransformDraftRequest): Promise<DraftJobResponse> => {
    return apiClient.post(`/api/v1/drafts/${draftId}/transform`, data)
  },

  exportMarkdown: async (draftId: string): Promise<Blob> => {
    // 인증이 필요한 엔드포인트이므로 토큰이 붙는 클라이언트로 받아야 한다.
    return apiClient.getBlob(`/api/v1/export/drafts/${draftId}/md`)
  },
}
