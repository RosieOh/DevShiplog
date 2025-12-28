import { NextResponse } from 'next/server'
import { apiClient } from '@/lib/api/client'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { email, password, name } = body

    if (!email || !password || !name) {
      return NextResponse.json(
        { message: '모든 필드를 입력해주세요.' },
        { status: 400 }
      )
    }

    // Backend API로 회원가입 요청
    const response = await apiClient.post('/api/v1/auth/register', {
      email,
      password,
      name,
    })

    return NextResponse.json(response)
  } catch (error: any) {
    console.error('Signup error:', error)
    return NextResponse.json(
      { message: error.response?.data?.message || '회원가입에 실패했습니다.' },
      { status: error.response?.status || 500 }
    )
  }
}

