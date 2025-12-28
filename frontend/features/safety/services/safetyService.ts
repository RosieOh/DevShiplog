import { apiClient } from '@/lib/api/client'

export interface RiskFinding {
  id: string
  category: string
  severity: string
  snippet: string
  location: {
    line: number
    column: number
    end_column: number
  }
  status: string
}

export interface ApplyFixRequest {
  finding_id: string
  action: 'mask' | 'delete' | 'ignore'
  reason?: string
}

export const safetyService = {
  scan: async (draftId: string): Promise<{ findings: RiskFinding[]; count: number }> => {
    return apiClient.post(`/api/v1/safety/drafts/${draftId}/scan`)
  },

  getFindings: async (draftId: string): Promise<RiskFinding[]> => {
    return apiClient.get(`/api/v1/safety/drafts/${draftId}/findings`)
  },

  applyFix: async (draftId: string, data: ApplyFixRequest): Promise<{ message: string }> => {
    return apiClient.post(`/api/v1/safety/drafts/${draftId}/apply`, data)
  },
}

