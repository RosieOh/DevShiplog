import { apiClient } from '@/lib/api/client'

export interface DraftStats {
  total: number
  by_type: Record<string, number>
  by_audience: Record<string, number>
  average_length: number
  style_profile_usage_rate: number
}

export interface WritingPattern {
  most_used_type: string
  most_used_audience: string
  preferred_length: string
  style_profile_usage_count: number
}

export interface TimeDistribution {
  by_hour: Record<string, number>
  by_day_of_week: Record<string, number>
}

export const analyticsService = {
  getDraftStats: async (): Promise<DraftStats> => {
    return apiClient.get('/api/v1/analytics/drafts')
  },

  getWritingPatterns: async (): Promise<WritingPattern> => {
    return apiClient.get('/api/v1/analytics/writing-patterns')
  },

  getTimeDistribution: async (): Promise<TimeDistribution> => {
    return apiClient.get('/api/v1/analytics/time-distribution')
  },
}

