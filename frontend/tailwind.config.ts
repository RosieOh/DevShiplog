import type { Config } from 'tailwindcss'

/**
 * 색은 app/globals.css 의 :root 토큰이 단일 출처다.
 * 여기서는 그 채널값을 알파 지원 형태로 감싸기만 한다 (bg-accent/20 이 동작하도록).
 */
const withAlpha = (token: string) => `rgb(var(--${token}) / <alpha-value>)`

const config: Config = {
  // 테마는 <html data-theme="dark"> 로 전환한다. 미디어쿼리만으로는
  // 사용자가 명시적으로 고른 값을 존중할 수 없다.
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './features/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: withAlpha('bg'),
        surface: {
          DEFAULT: withAlpha('surface'),
          2: withAlpha('surface-2'),
        },
        border: {
          DEFAULT: withAlpha('border'),
          subtle: withAlpha('border-subtle'),
        },
        ink: {
          DEFAULT: withAlpha('text'),
          muted: withAlpha('text-muted'),
          faint: withAlpha('text-faint'),
        },
        accent: {
          // 채움·테두리 전용. 텍스트로 쓰면 대비가 부족하다.
          DEFAULT: withAlpha('accent'),
          text: withAlpha('accent-text'),
          contrast: withAlpha('accent-contrast'),
        },
        danger: withAlpha('danger'),
        // 신선도는 이 제품의 핵심 어휘다. 화면마다 색을 직접 적으면 곧 어긋나고,
        // "이 초록이 그 초록인가" 를 매번 판단하게 된다.
        fresh: withAlpha('fresh'),
        aging: withAlpha('aging'),
        stale: withAlpha('stale'),
        warning: withAlpha('warning'),
      },
      borderRadius: {
        // 이 세계의 기본 곡률. 이전 세계의 32px 카드와 결별한다.
        DEFAULT: '4px',
        sm: '2px',
        md: '6px',
        lg: '8px',
      },
      boxShadow: {
        card: '0 1px 3px rgb(0 0 0 / 0.06), 0 1px 2px rgb(0 0 0 / 0.04)',
        'card-hover': '0 8px 20px rgb(0 0 0 / 0.10), 0 2px 6px rgb(0 0 0 / 0.06)',
        pop: '0 4px 16px rgb(0 0 0 / 0.12)',
      },
      fontFamily: {
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      // 신선도는 이 제품의 핵심 어휘다. 색을 화면마다 직접 적으면 곧 어긋난다.
      // (아래 세 색은 globals.css 에서 라이트/다크가 각각 정의된다.)
      minHeight: { touch: '44px' },
      minWidth: { touch: '44px' },
      /*
       * h-touch / w-touch 도 쓸 수 있어야 한다.
       * minHeight 만 정의해 두면 `h-touch` 는 존재하지 않는 클래스라 조용히 무시되고,
       * 아이콘 버튼이 아이콘 크기(20px)로 쪼그라든다. 실제로 헤더에서 그 일이 났다.
       */
      height: { touch: '44px' },
      width: { touch: '44px' },
      maxWidth: { content: '768px', shell: '1200px' },
      /*
       * 셸(1200px) 바깥 여백에 플로팅 바가 들어갈 수 있는 최소 폭.
       * 1200 + 바 62px + 여백 16px 을 양쪽에 두면 1356px 이고, 여유를 둬 1400 으로 잡았다.
       * xl(1280px)에서 띄우면 본문 위로 올라탄다.
       */
      screens: { wide: '1400px' },
    },
  },
  plugins: [],
}
export default config
