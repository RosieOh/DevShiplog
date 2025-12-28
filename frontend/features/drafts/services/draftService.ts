import { apiClient } from '@/lib/api/client'

export interface CreateDraftRequest {
  source_ids: string[]
  type: string
  audience: string
  length: string
  use_style_profile: boolean
  style_profile_id?: string
  user_id: string
}

export interface DraftResponse {
  id: string
  job_id: string
  status: string
}

export interface Draft {
  id: string
  status: string
  type: string
  audience: string
  length_preset: string
  tags?: string[]
  notes?: string
  checklist?: Array<{id: string, text: string, checked: boolean}>
  latest_version?: {
    version_no: number
    content_md: string
    meta_json: any
  }
}

export interface TransformDraftRequest {
  transform_type: string
  user_id: string
}

export interface UpdateDraftVersionRequest {
  content_md: string
  meta_json?: any
}

export const draftService = {
  create: async (data: CreateDraftRequest): Promise<DraftResponse> => {
    return apiClient.post('/api/v1/drafts', data)
  },

  get: async (draftId: string): Promise<Draft> => {
    return apiClient.get(`/api/v1/drafts/${draftId}`)
  },

  list: async (): Promise<Draft[]> => {
    return apiClient.get('/api/v1/drafts')
  },

  updateVersion: async (draftId: string, data: UpdateDraftVersionRequest): Promise<void> => {
    return apiClient.put(`/api/v1/drafts/${draftId}/version`, data)
  },

  transform: async (draftId: string, data: TransformDraftRequest): Promise<DraftResponse> => {
    return apiClient.post(`/api/v1/drafts/${draftId}/transform`, data)
  },

  getVersions: async (draftId: string): Promise<any[]> => {
    return apiClient.get(`/api/v1/drafts/${draftId}/versions`)
  },

  exportMarkdown: async (draftId: string): Promise<Blob> => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/export/drafts/${draftId}/export/md`)
    return response.blob()
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

