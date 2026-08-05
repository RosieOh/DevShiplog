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
  /** 저장할 때마다 오른다. 다음 저장에 base_revision 으로 되돌려 보낸다. */
  revision?: number
}

export interface Draft {
  id: string
  status: string
  type: string
  audience: string
  length_preset: string
  created_at: string | null
  latest_version: DraftVersion | null
  tags?: string[]
  notes?: string
  checklist?: Array<{ id: string; text: string; checked: boolean }>
}

export interface TransformDraftRequest {
  transform_type: string
}

export interface SaveContentRequest {
  content_md: string
  meta_json?: Record<string, unknown> | null
  /** 내가 마지막으로 읽은 revision. 그 사이에 다른 저장이 있었으면 서버가 409 를 낸다. */
  base_revision?: number
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

  delete: async (draftId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/drafts/${draftId}`)
  },

  update: async (draftId: string, data: { tags?: string[], notes?: string, checklist?: any[] }): Promise<void> => {
    return apiClient.put(`/api/v1/drafts/${draftId}`, data)
  },

  generateOutline: async (data: { source_ids: string[], type: string, audience: string, length: string }): Promise<any> => {
    return apiClient.post('/api/v1/drafts/generate-outline', data)
  },

  getOutline: async (draftId: string): Promise<any> => {
    return apiClient.get(`/api/v1/drafts/${draftId}/outline`)
  },

  updateOutline: async (draftId: string, outline: any): Promise<void> => {
    return apiClient.put(`/api/v1/drafts/${draftId}/outline`, { outline })
  },

  compareVersions: async (draftId: string, version1Id: string, version2Id: string): Promise<any> => {
    return apiClient.get(`/api/v1/drafts/${draftId}/compare?version1_id=${version1Id}&version2_id=${version2Id}`)
  },
}
