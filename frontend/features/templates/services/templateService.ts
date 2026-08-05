import { apiClient } from '@/lib/api/client'

export interface Template {
  id: string
  name: string
  type: string
  audience: string
  length_preset: string
  style_profile_id?: string
  created_at: string
}

export interface CreateTemplateRequest {
  name: string
  type: string
  audience: string
  length_preset: string
  style_profile_id?: string
}

export const templateService = {
  create: async (data: CreateTemplateRequest): Promise<Template> => {
    return apiClient.post('/api/v1/templates', data)
  },

  list: async (): Promise<Template[]> => {
    return apiClient.get('/api/v1/templates')
  },

  get: async (templateId: string): Promise<Template> => {
    return apiClient.get(`/api/v1/templates/${templateId}`)
  },

  delete: async (templateId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/templates/${templateId}`)
  },
}

