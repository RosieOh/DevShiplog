import { apiClient } from '@/lib/api/client'

export interface LikeResult {
  liked: boolean
  like_count: number
}

export interface FollowResult {
  following: boolean
  follower_count: number
}

export interface NotificationItem {
  id: string
  type: 'comment' | 'reply' | 'like' | 'follow' | 'signal_broken'
  actor: { handle: string; display_name: string; avatar_url: string | null }
  post: { title: string; url: string } | null
  read: boolean
  created_at: string | null
}

export const socialService = {
  toggleLike: (postId: string): Promise<LikeResult> =>
    apiClient.post(`/api/v1/social/posts/${postId}/like`),

  toggleFollow: (handle: string): Promise<FollowResult> =>
    apiClient.post(`/api/v1/social/users/${encodeURIComponent(handle)}/follow`),

  toggleBlock: (handle: string): Promise<{ blocked: boolean }> =>
    apiClient.post(`/api/v1/social/users/${encodeURIComponent(handle)}/block`),

  addComment: (postId: string, body: string, parentId?: string): Promise<{ id: string }> =>
    apiClient.post(`/api/v1/social/posts/${postId}/comments`, {
      body,
      parent_id: parentId ?? null,
    }),

  updateComment: (commentId: string, body: string): Promise<{ id: string; body: string }> =>
    apiClient.put(`/api/v1/social/comments/${commentId}`, { body }),

  deleteComment: (commentId: string): Promise<{ deleted: boolean }> =>
    apiClient.delete(`/api/v1/social/comments/${commentId}`),

  report: (
    targetType: 'post' | 'comment' | 'user',
    targetId: string,
    reason: string,
    detail = ''
  ): Promise<{ reported: boolean; already: boolean; auto_hidden: boolean }> =>
    apiClient.post('/api/v1/social/reports', {
      target_type: targetType,
      target_id: targetId,
      reason,
      detail,
    }),

  notifications: (): Promise<{ unread_count: number; items: NotificationItem[] }> =>
    apiClient.get('/api/v1/social/notifications'),

  markNotificationsRead: (): Promise<{ updated: number }> =>
    apiClient.post('/api/v1/social/notifications/read'),

  followingFeed: (): Promise<{
    items: {
      id: string
      title: string
      summary: string | null
      url: string
      published_at: string | null
      like_count: number
      comment_count: number
      author: { handle: string; display_name: string }
    }[]
    has_more: boolean
  }> => apiClient.get('/api/v1/social/feed/following'),
}
