import { useState } from 'react'
import { draftService, CreateDraftRequest } from '../services/draftService'

export const useDraftGeneration = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [draftId, setDraftId] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)

  const generateDraft = async (request: CreateDraftRequest) => {
    setLoading(true)
    setError(null)
    try {
      const result = await draftService.create(request)
      setDraftId(result.id)
      setJobId(result.job_id)
      return result
    } catch (err: any) {
      setError(err.message || 'Draft 생성 실패')
      throw err
    } finally {
      setLoading(false)
    }
  }

  return {
    generateDraft,
    loading,
    error,
    draftId,
    jobId,
  }
}

