import { apiClient } from '@/lib/api/client'

export interface CreateStyleProfileRequest {
  blog_url: string
  sample_count: number
  user_id: string
}

export interface StyleProfileResponse {
  id: string
  status: string
  blog_url: string
  sample_count: number
}

export const styleProfileService = {
  create: async (data: CreateStyleProfileRequest): Promise<StyleProfileResponse> => {
    return apiClient.post('/api/v1/style-profiles', data)
  },

  get: async (profileId: string): Promise<StyleProfileResponse> => {
    return apiClient.get(`/api/v1/style-profiles/${profileId}`)
  },
}

