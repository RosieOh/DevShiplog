import type { MetadataRoute } from 'next'
import { SITE_URL } from '@/lib/api/public'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: [
        // 로그인이 필요한 앱 영역은 크롤링해도 아무것도 못 얻는다.
        '/dashboard',
        '/drafts/',
        '/settings',
        '/notifications',
        '/onboarding/',
        '/auth/',
        '/api/',
        // 검색 결과는 무한 조합이라 중복 콘텐츠가 된다.
        '/search',
      ],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  }
}
