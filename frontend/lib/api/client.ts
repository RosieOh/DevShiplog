import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios'
import { getSession, signOut } from 'next-auth/react'

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** 백엔드가 내려주는 오류 본문 */
interface ApiErrorBody {
  detail?: string
  [key: string]: unknown
}

/** 사용자에게 보여줄 메시지를 담은 오류 */
export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    /*
     * 응답 본문 전체. detail 만으로는 부족한 경우가 있다.
     * 예: 409 충돌은 "서버의 현재 내용" 을 같이 줘야 사용자가 고를 수 있다.
     */
    readonly body?: ApiErrorBody
  ) {
    super(message)
    this.name = 'ApiRequestError'
  }
}

function toApiError(error: AxiosError<ApiErrorBody>): ApiRequestError {
  const status = error.response?.status
  const body = error.response?.data
  const detail = body?.detail

  if (detail) return new ApiRequestError(detail, status, body)
  if (status === 429) return new ApiRequestError('사용 한도를 초과했습니다.', status, body)
  if (status && status >= 500) return new ApiRequestError('서버 오류가 발생했습니다.', status, body)
  if (error.code === 'ECONNABORTED')
    return new ApiRequestError('요청 시간이 초과되었습니다.', status, body)
  return new ApiRequestError(error.message || '요청에 실패했습니다.', status, body)
}

/**
 * 브라우저 전용 API 클라이언트.
 * 서버(Route Handler, NextAuth 콜백)에서는 lib/api/server.ts 를 쓴다.
 */
class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30_000,
      headers: { 'Content-Type': 'application/json' },
    })

    this.client.interceptors.request.use(async (config) => {
      const session = await getSession()
      if (session?.accessToken) {
        config.headers.Authorization = `Bearer ${session.accessToken}`
      }
      return config
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiErrorBody>) => {
        // 토큰 만료 시 세션까지 정리해야 리다이렉트 루프에 빠지지 않는다.
        if (error.response?.status === 401 && typeof window !== 'undefined') {
          void signOut({ callbackUrl: '/auth/login' })
        }
        return Promise.reject(toApiError(error))
      }
    )
  }

  /** SSE 용 액세스 토큰. EventSource 는 헤더를 붙일 수 없어 쿼리로 넘긴다. */
  async getAccessToken(): Promise<string | null> {
    const session = await getSession()
    return session?.accessToken ?? null
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config)
    return response.data
  }

  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config)
    return response.data
  }

  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config)
    return response.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config)
    return response.data
  }

  /**
   * 멀티파트 업로드.
   * Content-Type 을 직접 지정하면 boundary 가 빠져 서버가 파싱하지 못한다.
   * 브라우저가 채우도록 undefined 로 지운다.
   */
  async postForm<T>(url: string, form: FormData): Promise<T> {
    const response = await this.client.post<T>(url, form, {
      headers: { 'Content-Type': undefined },
    })
    return response.data
  }

  /** 인증 헤더를 포함해 바이너리를 내려받는다. */
  async getBlob(url: string): Promise<Blob> {
    const response = await this.client.get<Blob>(url, { responseType: 'blob' })
    return response.data
  }

  /**
   * 인증된 SSE 연결을 만든다.
   * EventSource 는 커스텀 헤더를 지원하지 않으므로 토큰을 쿼리로 전달한다.
   */
  async createEventSource(path: string): Promise<EventSource> {
    const token = await this.getAccessToken()
    const separator = path.includes('?') ? '&' : '?'
    const suffix = token ? `${separator}token=${encodeURIComponent(token)}` : ''
    return new EventSource(`${API_BASE_URL}${path}${suffix}`)
  }
}

export const apiClient = new ApiClient()
