/**
 * 프로필 이미지.
 *
 * 아직 이미지 업로드가 없어 대부분 비어 있다. 빈 원을 두면 목록이 허전해지므로
 * handle 에서 결정적으로 색과 이니셜을 만들어 채운다 (같은 사람은 항상 같은 색).
 */

const PALETTE = [
  { bg: '#e6fcf5', fg: '#087f5b' }, // teal
  { bg: '#e7f5ff', fg: '#1864ab' }, // blue
  { bg: '#fff4e6', fg: '#d9480f' }, // orange
  { bg: '#f3f0ff', fg: '#5f3dc4' }, // violet
  { bg: '#fff0f6', fg: '#a61e4d' }, // pink
  { bg: '#ebfbee', fg: '#2b8a3e' }, // green
]

function hash(value: string): number {
  let h = 0
  for (let i = 0; i < value.length; i += 1) {
    h = (h * 31 + value.charCodeAt(i)) >>> 0
  }
  return h
}

interface Props {
  handle: string
  displayName?: string | null
  src?: string | null
  size?: number
  className?: string
}

export default function Avatar({ handle, displayName, src, size = 24, className }: Props) {
  const label = (displayName || handle || '?').trim()
  const initial = [...label][0]?.toUpperCase() ?? '?'
  const tone = PALETTE[hash(handle || label) % PALETTE.length]

  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        className={`shrink-0 rounded-full object-cover ${className ?? ''}`}
        style={{ width: size, height: size }}
      />
    )
  }

  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-full font-bold leading-none ${className ?? ''}`}
      style={{
        width: size,
        height: size,
        backgroundColor: tone.bg,
        color: tone.fg,
        fontSize: Math.max(10, Math.round(size * 0.44)),
      }}
    >
      {initial}
    </span>
  )
}
