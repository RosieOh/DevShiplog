import type { Config } from 'tailwindcss'

/**
 * 색은 app/globals.css 의 :root 토큰이 단일 출처다.
 * 여기서는 그 채널값을 알파 지원 형태로 감싸기만 한다 (bg-accent/20 같은 표현이 동작하도록).
 */
const withAlpha = (token: string) => `rgb(var(--${token}) / <alpha-value>)`

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './features/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas: withAlpha('canvas'),
        surface: {
          DEFAULT: withAlpha('surface'),
          dark: withAlpha('surface-dark'),
        },
        ink: {
          DEFAULT: withAlpha('ink'),
          muted: withAlpha('ink-muted'),
        },
        line: withAlpha('line'),
        accent: {
          // 배경 전용. 전경으로 쓰면 대비가 1.13:1 이라 보이지 않는다.
          DEFAULT: withAlpha('accent'),
          // 전경용 파생색 (canvas 대비 5.8:1)
          ink: withAlpha('accent-ink'),
        },
      },
      fontFamily: {
        // next/font 가 주입하는 변수를 쓴다 (app/layout.tsx 참고).
        sans: ['var(--font-sans)', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      },
      minHeight: {
        touch: '44px',
      },
      minWidth: {
        touch: '44px',
      },
    },
  },
  plugins: [],
}
export default config
