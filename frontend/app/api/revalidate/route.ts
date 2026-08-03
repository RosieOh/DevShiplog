import { NextResponse } from 'next/server'
import { revalidateTag } from 'next/cache'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

/**
 * 공개 페이지 캐시 무효화.
 *
 * 공개 글은 서버에서 렌더되고 캐시된다(그래야 검색 크롤러가 읽는다).
 * 그래서 발행·댓글 같은 쓰기가 일어나면 누군가 캐시를 깨줘야 한다.
 *
 * 두 가지 호출자를 허용한다:
 *  1) 백엔드 — 공유 시크릿. 브라우저를 거치지 않는 경로(모바일 앱, CLI, 배치)도
 *     캐시가 갱신되므로 이쪽이 주 경로다.
 *  2) 로그인한 브라우저 — 세션. 백엔드 통지가 설정되지 않은 환경의 보조 경로.
 */

// 임의 태그를 무효화해 캐시를 통째로 날리는 것을 막는다.
const ALLOWED = /^(feed|blog:[\w-]+|post:[\w-]+:.+)$/

export async function POST(request: Request) {
  const secret = process.env.REVALIDATE_SECRET
  const provided = request.headers.get('x-revalidate-secret')
  const fromBackend = Boolean(secret && provided && provided === secret)

  if (!fromBackend) {
    const session = await getServerSession(authOptions)
    if (!session) {
      return NextResponse.json({ message: '인증이 필요합니다.' }, { status: 401 })
    }
  }

  let tags: unknown
  try {
    ;({ tags } = await request.json())
  } catch {
    return NextResponse.json({ message: '잘못된 요청입니다.' }, { status: 400 })
  }

  if (!Array.isArray(tags)) {
    return NextResponse.json({ message: 'tags 배열이 필요합니다.' }, { status: 400 })
  }

  const applied: string[] = []
  for (const tag of tags) {
    if (typeof tag === 'string' && ALLOWED.test(tag)) {
      revalidateTag(tag)
      applied.push(tag)
    }
  }

  return NextResponse.json({ revalidated: applied })
}
