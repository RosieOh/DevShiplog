/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    // instrumentation.ts (캐시 무효화 Redis 구독) 은 Next 14 에서 옵트인이다.
    instrumentationHook: true,
    /*
     * ioredis 는 번들에 넣지 않고 Node 가 직접 require 하게 한다.
     * instrumentation 은 edge 런타임용으로도 컴파일되는데, 거기에는 net/dns/tls 가
     * 없어서 번들링을 시도하는 것만으로 빌드가 깨진다 (실행은 안 되더라도).
     */
    serverComponentsExternalPackages: ['ioredis'],
  },
  async rewrites() {
    return [
      /*
       * 공개 블로그 주소: /@handle, /@handle/slug
       *
       * Next.js 는 `@folder` 를 병렬 라우트(named slot)로 예약해 두어서
       * app/@[handle] 같은 폴더를 만들 수 없다. 실제 라우트는 /blog/... 에 두고
       * 사용자에게 보이는 주소만 /@handle 로 맞춘다.
       *
       * 구체적인 패턴이 먼저 와야 한다 (배열 순서대로 평가된다).
       */
      { source: '/@:handle/series/:seriesSlug', destination: '/blog/:handle/series/:seriesSlug' },
      { source: '/@:handle/:slug', destination: '/blog/:handle/:slug' },
      { source: '/@:handle', destination: '/blog/:handle' },

      {
        /*
         * 백엔드 프록시.
         *
         * source 를 '/api/:path*' 로 두면 NextAuth 가 자기 것으로 써야 하는
         * /api/auth/session, /csrf, /callback/* 까지 FastAPI 로 넘어가 로그인이 깨진다.
         * (rewrites() 가 배열을 반환하면 afterFiles 로 동작하고, afterFiles 는
         *  [...nextauth] 같은 "동적" 라우트보다 먼저 평가된다.)
         *
         * 백엔드가 실제로 서비스하는 접두사만 넘긴다.
         */
        source: '/api/v1/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/:path*`,
      },
      {
        /*
         * 업로드된 이미지.
         *
         * 백엔드는 커버/아바타 주소를 '/uploads/...' 같은 상대 경로로 돌려준다.
         * 도메인을 박아 두면 환경이 바뀔 때마다 DB 에 남은 주소가 전부 깨지기 때문이다.
         * 대신 브라우저가 그 경로를 프론트 도메인에서 찾으므로 여기서 넘겨줘야 한다.
         * (S3 로 옮기면 절대 URL 이 내려오고 이 규칙은 그냥 안 타게 된다.)
         */
        source: '/uploads/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/uploads/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
