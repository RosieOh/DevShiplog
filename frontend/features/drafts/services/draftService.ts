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
}

