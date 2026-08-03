/**
 * 서버 전용 API 클라이언트.
 *
 * lib/api/client.ts 는 요청 인터셉터에서 next-auth/react 의 getSession() 을 부른다.
 * 그건 브라우저 전용 API라, Route Handler 나 NextAuth 의 authorize() 콜백 같은
 * 서버 컨텍스트에서 쓰면 세션 조회가 자기 자신을 다시 호출하는 꼴이 된다.
 * 서버에서는 반드시 이 모듈을 쓴다.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly data?: unknown
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function messageFrom(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

export async function serverFetch<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {}
): Promise<T> {
  const { json, headers, ...rest } = init

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    cache: 'no-store',
  })

  const body = await parseBody(response)

  if (!response.ok) {
    throw new ApiError(
      messageFrom(body, `요청에 실패했습니다 (HTTP ${response.status})`),
      response.status,
      body
    )
  }

  return body as T
}

/** 백엔드 인증 응답 형태 */
export interface BackendAuthResponse {
  access_token: string
  token_type: string
  user: {
    id: string
    email: string
    name: string | null
  }
}
