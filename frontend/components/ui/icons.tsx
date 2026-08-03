/**
 * 아이콘 세트.
 *
 * 이모지(📋 ⬇️ ⚠️ ✕)를 아이콘 자리에 쓰면 플랫폼마다 다르게 렌더링되고
 * 색·굵기·크기를 제어할 수 없다. 모두 동일한 24 그리드 / 1.75 스트로크로 그린다.
 *
 * 텍스트 레이블과 함께 쓰일 때는 기본값인 aria-hidden 을 유지하고,
 * 아이콘만 있는 버튼에서는 버튼 쪽에 aria-label 을 단다.
 */

interface IconProps {
  className?: string
}

const base = 'shrink-0'

function Svg({ className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      className={`${base} ${className ?? 'w-5 h-5'}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  )
}

export function ClipboardIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="8" y="3" width="8" height="4" rx="1.5" />
      <path d="M9 5H6.5A1.5 1.5 0 0 0 5 6.5v13A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5v-13A1.5 1.5 0 0 0 17.5 5H15" />
    </Svg>
  )
}

export function DownloadIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3v12" />
      <path d="m7 11 5 5 5-5" />
      <path d="M4 20h16" />
    </Svg>
  )
}

export function AlertIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10.3 4.2 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z" />
      <path d="M12 9.5v4" />
      <path d="M12 17h.01" />
    </Svg>
  )
}

export function CheckCircleIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </Svg>
  )
}

export function HeartIcon({ className, filled }: IconProps & { filled?: boolean }) {
  return (
    <svg
      className={`${base} ${className ?? 'w-5 h-5'}`}
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M12 20.5S3.8 15.4 3.8 9.9A4.6 4.6 0 0 1 12 7.1a4.6 4.6 0 0 1 8.2 2.8c0 5.5-8.2 10.6-8.2 10.6Z" />
    </svg>
  )
}


export function CloseIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m6 6 12 12" />
      <path d="m18 6-12 12" />
    </Svg>
  )
}

export function MenuIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </Svg>
  )
}

export function PlusIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </Svg>
  )
}
