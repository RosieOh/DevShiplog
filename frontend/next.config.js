/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        /*
         * 백엔드 프록시.
         *
         * 예전에는 source 가 '/api/:path*' 였는데, 이러면 NextAuth 가 자기 것으로 써야 하는
         * /api/auth/session, /api/auth/csrf, /api/auth/callback/* 까지 FastAPI 로 넘어가
         * 로그인이 통째로 깨진다.
         * (rewrites() 가 배열을 반환하면 afterFiles 로 동작하고, afterFiles 는
         *  [...nextauth] 같은 "동적" 라우트보다 먼저 평가된다. 정적 라우트만 리라이트를 이긴다.)
         *
         * 백엔드가 실제로 서비스하는 접두사만 넘긴다.
         */
        source: '/api/v1/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
