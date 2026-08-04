'use client'

import { useEffect, useState } from 'react'

const SPLINE_SRC =
  'https://my.spline.design/nexbotrobotcharacterconcept-Mu1XiRzONHbkJyjSPqGS79ut/'

/**
 * 랜딩 히어로의 3D 장면.
 *
 * 이전에는 외부 WebGL 씬을 첫 페인트와 동시에 불러와 LCP 를 직접 밀어냈다.
 * 지금은
 *  1) 브라우저가 한가해진 뒤에 mount 하고 (초기 렌더 경로에서 제외)
 *  2) 모션 감소를 선택한 사용자에게는 아예 띄우지 않으며
 *  3) 그동안/대신 정적 그라디언트를 보여줘 레이아웃이 흔들리지 않게 한다.
 */
export default function HeroRobot() {
  const [showScene, setShowScene] = useState(false)

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches
    if (prefersReducedMotion) return

    const show = () => setShowScene(true)

    if (typeof window.requestIdleCallback === 'function') {
      const handle = window.requestIdleCallback(show, { timeout: 2500 })
      return () => window.cancelIdleCallback?.(handle)
    }

    // requestIdleCallback 미지원 브라우저(Safari 등)는 짧은 지연으로 대체한다.
    const timer = window.setTimeout(show, 1200)
    return () => window.clearTimeout(timer)
  }, [])

  return (
    <div className="absolute inset-0 z-0 w-full h-full overflow-hidden" aria-hidden="true">
      {/* 씬이 없거나 아직 로드 전일 때의 바탕. 로드 후에도 뒤에 깔려 빈 프레임을 막는다. */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_40%,rgb(var(--accent)/0.35),transparent_60%)]" />
      {showScene && (
        <iframe
          src={SPLINE_SRC}
          title="Devshiplog 소개 3D 장면"
          loading="lazy"
          width="100%"
          height="100%"
          className="relative pointer-events-auto border-0"
          style={{ filter: 'contrast(1.2) brightness(0.9) saturate(1.1)' }}
          allow="fullscreen"
        />
      )}
      {/*
        헤드라인 가독성 스크림.
        장면이 화면 전체를 채우면서 좌측 텍스트 컬럼(최대 672px)을 가려
        1440 에서 "기술 글 작성," 이 로봇 머리에 묻혔다.
        장면 내용이 무엇이든 왼쪽은 항상 읽히도록 페이지 배경색으로 덮는다.
      */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-surface via-surface/85 to-transparent to-65%" />
    </div>
  )
}
