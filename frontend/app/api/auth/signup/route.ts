import { NextResponse } from 'next/server'
import { ApiError, BackendAuthResponse, serverFetch } from '@/lib/api/server'

export async function POST(request: Request) {
  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ message: '잘못된 요청 형식입니다.' }, { status: 400 })
  }

  const { email, password, name } = (body ?? {}) as {
    email?: string
    password?: string
    name?: string
  }

  if (!email || !password || !name) {
    return NextResponse.json({ message: '모든 필드를 입력해주세요.' }, { status: 400 })
  }
  if (password.length < 8) {
    return NextResponse.json({ message: '비밀번호는 8자 이상이어야 합니다.' }, { status: 400 })
  }

  try {
    const response = await serverFetch<BackendAuthResponse>('/api/v1/auth/register', {
      method: 'POST',
      json: { email, password, name },
    })

    // 액세스 토큰은 브라우저로 내려보내지 않는다. 가입 직후 로그인 플로우를 태운다.
    return NextResponse.json({ user: response.user }, { status: 201 })
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ message: error.message }, { status: error.status })
    }
    console.error('Signup error:', error)
    return NextResponse.json({ message: '회원가입에 실패했습니다.' }, { status: 500 })
  }
}
