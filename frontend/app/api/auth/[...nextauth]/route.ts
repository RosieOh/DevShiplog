import NextAuth from 'next-auth'
import { authOptions } from '@/lib/auth'

// route.ts 에서는 GET/POST 등 정해진 핸들러만 export 할 수 있다.
// NextAuth 설정은 @/lib/auth 에 있다.
const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }
