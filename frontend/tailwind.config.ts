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
      minHeight: { touch: '44px' },
      minWidth: { touch: '44px' },
      maxWidth: { content: '768px', shell: '1200px' },
    },
  },
  plugins: [],
}
export default config
