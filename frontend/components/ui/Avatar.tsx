/**
 * 프로필 이미지.
 *
 * 아직 이미지 업로드가 없어 대부분 비어 있다. 빈 원을 두면 목록이 허전해지므로
 * handle 에서 결정적으로 색과 이니셜을 만들어 채운다 (같은 사람은 항상 같은 색).
 */

/*
 * 배경/글자 짝은 전부 4.5:1 이상이어야 한다. 이니셜은 장식이 아니라 "누구의 글인가" 를
 * 알려주는 정보이기 때문이다. 아래 대비값은 실측한 것이고, 색을 바꿀 때 같이 확인해야 한다.
 *
 * 처음에 teal-9/green-9 (#087f5b, #2b8a3e) 를 썼다가 각각 4.4:1, 4.07:1 이 나와
 * 한 단계 더 어두운 색으로 내렸다. Open Color 의 -9 가 항상 AA 를 넘는 것은 아니다.
 */
const PALETTE = [
  { bg: '#e6fcf5', fg: '#0b7285' }, // teal   — 5.21:1
  { bg: '#e7f5ff', fg: '#1864ab' }, // blue   — 5.48:1
  { bg: '#fff4e6', fg: '#c92a2a' }, // orange — 5.02:1
  { bg: '#f3f0ff', fg: '#5f3dc4' }, // violet — 6.34:1
  { bg: '#fff0f6', fg: '#a61e4d' }, // pink   — 6.54:1
  { bg: '#ebfbee', fg: '#2b6a30' }, // green  — 6.10:1
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
