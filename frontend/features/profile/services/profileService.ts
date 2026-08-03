import { apiClient } from '@/lib/api/client'

export interface MyProfile {
  id: string
  email: string
  handle: string | null
  display_name: string | null
  bio: string | null
  avatar_url: string | null
  post_count: number
  follower_count: number
  following_count: number
  /** handle 이 없으면 발행할 수 없다 */
  needs_handle: boolean
}

export interface ProfileUpdate {
  handle?: string
  display_name?: string
  bio?: string
  avatar_url?: string
}

export const profileService = {
  me: (): Promise<MyProfile> => apiClient.get('/api/v1/profile/me'),

  update: (
    data: ProfileUpdate
  ): Promise<MyProfile & { handle_changed: boolean }> =>
    apiClient.put('/api/v1/profile/me', data),

  checkHandle: (
    handle: string
  ): Promise<{ available: boolean; handle: string | null; reason: string | null }> =>
    apiClient.get(`/api/v1/profile/handle-available?handle=${encodeURIComponent(handle)}`),
}
