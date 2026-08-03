import { NextAuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import { ApiError, BackendAuthResponse, serverFetch } from '@/lib/api/server'

/**
 * NextAuth 설정.
 *
 * App Router 의 route.ts 는 GET/POST 같은 정해진 이름 외의 export 를 허용하지 않아
 * (빌드 시 타입 에러) 설정을 별도 모듈로 둔다. 서버 컴포넌트에서
 * getServerSession(authOptions) 로도 재사용할 수 있다.
 */
export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null
        }

        try {
          // 서버 컨텍스트이므로 브라우저용 apiClient(getSession 의존)를 쓰면 안 된다.
          const response = await serverFetch<BackendAuthResponse>('/api/v1/auth/login', {
            method: 'POST',
            json: { email: credentials.email, password: credentials.password },
          })

          if (!response?.user) return null

          return {
            id: response.user.id,
            email: response.user.email,
            name: response.user.name ?? '',
            accessToken: response.access_token,
          }
        } catch (error) {
          // 자격 증명 오류(401)는 정상 흐름이므로 서버 오류만 로그로 남긴다.
          if (!(error instanceof ApiError) || error.status >= 500) {
            console.error('Auth error:', error)
          }
          return null
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = (user as { accessToken?: string }).accessToken
        token.id = user.id
      }
      return token
    },
    async session({ session, token }) {
      session.user = {
        id: (token.id as string) ?? '',
        email: (token.email as string) ?? '',
        name: (token.name as string) ?? '',
      }
      session.accessToken = (token.accessToken as string) ?? ''
      return session
    },
  },
  pages: {
    signIn: '/auth/login',
  },
  session: {
    strategy: 'jwt',
  },
}
