import { apiClient } from '@/lib/api/client'

export interface PublishRequest {
  draft_id: string
  title: string
  tags: string[]
  cover_url?: string
  /** 민감정보 경고를 확인하고도 진행하겠다는 명시적 동의 */
  allow_sensitive?: boolean
}

export interface PublishResult {
  id: string
  slug: string
  url: string
  status: string
  created: boolean
  tags: string[]
  sensitive_findings: number
}

export interface MyPost {
  id: string
  slug: string
  title: string
  status: 'published' | 'unlisted' | 'hidden'
  published_at: string | null
  like_count: number
  comment_count: number
  view_count: number
  url: string | null
  draft_id: string | null
}

export interface DraftPublishState {
  published: boolean
  id?: string
  slug?: string
  title?: string
  status?: string
  tags?: string[]
  url?: string | null
}

export const postService = {
  publish: (data: PublishRequest): Promise<PublishResult> =>
    apiClient.post('/api/v1/posts', data),

  mine: (): Promise<MyPost[]> => apiClient.get('/api/v1/posts/mine'),

  forDraft: (draftId: string): Promise<DraftPublishState> =>
    apiClient.get(`/api/v1/posts/by-draft/${draftId}`),

  unpublish: (postId: string): Promise<{ id: string; status: string }> =>
    apiClient.post(`/api/v1/posts/${postId}/unpublish`),

  remove: (postId: string): Promise<{ deleted: boolean }> =>
    apiClient.delete(`/api/v1/posts/${postId}`),
}
