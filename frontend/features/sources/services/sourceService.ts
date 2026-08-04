import { apiClient } from '@/lib/api/client'

export interface SourceResponse {
  /** 추출에 실패하면 저장하지 않으므로 id 가 없다 */
  id: string | null
  type: string
  title: string
  status: 'succeeded' | 'failed'
  error: string | null
}

/** urls 또는 raw_text 중 하나만 채워 보낸다 (백엔드에서 검증) */
interface ExtractPayload {
  urls?: string[]
  raw_text?: string
}

export const sourceService = {
  extractURLs: async (urls: string[]): Promise<SourceResponse[]> => {
    const payload: ExtractPayload = { urls }
    return apiClient.post('/api/v1/sources/extract', payload)
  },

  extractText: async (rawText: string): Promise<SourceResponse[]> => {
    const payload: ExtractPayload = { raw_text: rawText }
    return apiClient.post('/api/v1/sources/extract', payload)
  },
}
