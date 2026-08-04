import { apiClient } from '@/lib/api/client'

export interface UploadResult {
  url: string
  key: string
  size: number
  content_type: string
  /** { original, w1200, w400 } — 만들어진 것만 담긴다. */
  variants: Record<string, string>
}

/**
 * 이미지 업로드.
 *
 * 화면에 쓸 주소는 url 하나면 된다. 서버가 리사이즈본을 골라 넣어 준다.
 * variants 는 원본이 필요할 때(다운로드, 확대 보기) 쓴다.
 */
export const uploadService = {
  image(file: File): Promise<UploadResult> {
    const form = new FormData()
    form.append('file', file)
    return apiClient.postForm<UploadResult>('/api/v1/uploads/images', form)
  },

  avatar(file: File): Promise<UploadResult> {
    const form = new FormData()
    form.append('file', file)
    return apiClient.postForm<UploadResult>('/api/v1/uploads/avatar', form)
  },
}
