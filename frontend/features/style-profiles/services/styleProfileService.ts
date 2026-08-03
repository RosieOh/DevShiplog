import { apiClient } from '@/lib/api/client'

export interface CreateStyleProfileRequest {
  blog_url: string
  sample_count: number
}

export interface StyleProfileResponse {
  id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  blog_url: string
  sample_count: number
  profile_json: Record<string, unknown> | null
  error_text: string | null
}

export const styleProfileService = {
  create: async (data: CreateStyleProfileRequest): Promise<StyleProfileResponse> => {
    return apiClient.post('/api/v1/style-profiles', data)
  },

  get: async (profileId: string): Promise<StyleProfileResponse> => {
    return apiClient.get(`/api/v1/style-profiles/${profileId}`)
  },

  list: async (): Promise<StyleProfileResponse[]> => {
    return apiClient.get('/api/v1/style-profiles')
  },
}
