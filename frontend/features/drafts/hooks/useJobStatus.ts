import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api/client'

export interface JobStatus {
  id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  progress: number
  result_ref?: any
  error_text?: string
}

export const useJobStatus = (jobId: string | null) => {
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchJobStatus = async () => {
    if (!jobId) return

    setLoading(true)
    try {
      const status = await apiClient.get<JobStatus>(`/api/v1/jobs/${jobId}`)
      setJobStatus(status)
      return status
    } catch (err) {
      console.error('Failed to fetch job status:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!jobId) return

    fetchJobStatus()
    const interval = setInterval(fetchJobStatus, 2000) // 2초마다 폴링

    return () => clearInterval(interval)
  }, [jobId])

  return {
    jobStatus,
    loading,
    refetch: fetchJobStatus,
  }
}

