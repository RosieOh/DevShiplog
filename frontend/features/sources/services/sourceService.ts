import { apiClient } from '@/lib/api/client'

export interface ExtractURLsRequest {
  urls: string[]
  user_id: string
}

export interface ExtractTextRequest {
  raw_text: string
  user_id: string
}

export interface SourceResponse {
  id: string
  type: string
  title: string
  status: string
}

export const sourceService = {
  extractURLs: async (data: ExtractURLsRequest): Promise<SourceResponse[]> => {
    return apiClient.post('/api/v1/sources/extract', data)
  },

  extractText: async (data: ExtractTextRequest): Promise<SourceResponse[]> => {
    return apiClient.post('/api/v1/sources/extract', data)
  },
}

