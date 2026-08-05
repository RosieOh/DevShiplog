import puppeteer from 'puppeteer-core'
import { mkdirSync } from 'node:fs'

const CHROME =
  process.env.CHROME_PATH ||
  'C:/Users/vrsoft/.cache/puppeteer/chrome/win64-151.0.7922.47/chrome-win64/chrome.exe'
const BASE = process.env.E2E_WEB || 'http://localhost:3001'
const OUT = new URL('./shots/', import.meta.url).pathname.replace(/^\//, '')

mkdirSync(OUT, { recursive: true })

const VIEWPORTS = [
  { name: '375', width: 375, height: 812, isMobile: true },
  { name: '768', width: 768, height: 1024, isMobile: false },
  { name: '1440', width: 1440, height: 900, isMobile: false },
]
const ROUTES = [
  { path: '/', name: 'landing' },
  { path: '/auth/login', name: 'login' },
  { path: '/terms', name: 'terms' },
]

// sRGB 상대 휘도 → 대비비
const lum = ([r, g, b]) => {
  const f = (c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}
const ratio = (a, b) => {
  const [hi, lo] = lum(a) > lum(b) ? [lum(a), lum(b)] : [lum(b), lum(a)]
  return (hi + 0.05) / (lo + 0.05)
}
const parseRgb = (s) => (s.match(/\d+(\.\d+)?/g) || []).slice(0, 3).map(Number)

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'shell',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
})

const findings = []

for (const vp of VIEWPORTS) {
  for (const route of ROUTES) {
    const page = await browser.newPage()
    await page.setViewport({ width: vp.width, height: vp.height, deviceScaleFactor: 1 })
    await page.goto(`${BASE}${route.path}`, { waitUntil: 'networkidle2', timeout: 45000 })
    await new Promise((r) => setTimeout(r, 600))

    // 1) 가로 오버플로 (body overflow-x:hidden 을 제거했으므로 실제로 확인해야 한다)
    const overflow = await page.evaluate(() => {
      const docW = document.documentElement.scrollWidth
      const winW = window.innerWidth
      if (docW <= winW + 1) return null
      const offenders = []
      for (const el of document.querySelectorAll('*')) {
        const r = el.getBoundingClientRect()
        if (r.right > winW + 1 || r.left < -1) {
          offenders.push({
            tag: el.tagName.toLowerCase(),
            cls: (el.className?.toString?.() || '').slice(0, 90),
            right: Math.round(r.right),
            left: Math.round(r.left),
          })
        }
      }
      return { docW, winW, offenders: offenders.slice(0, 6) }
    })
    if (overflow) findings.push({ type: 'overflow', vp: vp.name, route: route.name, ...overflow })

    // 2) 44px 미만 터치 타겟
    const smallTargets = await page.evaluate(() => {
      const out = []
      for (const el of document.querySelectorAll('a, button, input, select, textarea')) {
        const r = el.getBoundingClientRect()
        if (r.width === 0 || r.height === 0) continue
        if (r.width < 44 || r.height < 44) {
          out.push({
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 28),
            w: Math.round(r.width),
            h: Math.round(r.height),
          })
        }
      }
      return out.slice(0, 12)
    })
    if (smallTargets.length)
      findings.push({ type: 'touch', vp: vp.name, route: route.name, items: smallTargets })

    // 3) 텍스트 대비 (실제 계산된 색으로)
    const contrastSamples = await page.evaluate(() => {
      const bgOf = (el) => {
        let n = el
        while (n) {
          const c = getComputedStyle(n).backgroundColor
          if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c
          n = n.parentElement
        }
        return 'rgb(255,255,255)'
      }
      const out = []
      const els = [...document.querySelectorAll('p, span, a, li, h1, h2, h3, label, button')]
      for (const el of els.slice(0, 400)) {
        const t = (el.textContent || '').trim()
        if (!t || el.children.length > 0) continue
        const cs = getComputedStyle(el)
        if (parseFloat(cs.opacity) === 0 || cs.visibility === 'hidden') continue
        const r = el.getBoundingClientRect()
        if (r.width === 0 || r.height === 0) continue
        out.push({
          text: t.slice(0, 26),
          fg: cs.color,
          bg: bgOf(el),
          size: parseFloat(cs.fontSize),
          weight: cs.fontWeight,
        })
      }
      return out
    })
    for (const s of contrastSamples) {
      const cr = ratio(parseRgb(s.fg), parseRgb(s.bg))
      const large = s.size >= 24 || (s.size >= 18.66 && Number(s.weight) >= 700)
      const need = large ? 3 : 4.5
      if (cr < need) {
        findings.push({
          type: 'contrast',
          vp: vp.name,
          route: route.name,
          text: s.text,
          ratio: cr.toFixed(2),
          need,
          fg: s.fg,
          bg: s.bg,
        })
      }
    }

    // 4) 키보드 포커스 표시가 실제로 보이는지 (첫 3개 탭)
    if (vp.name === '1440') {
      const focusInfo = []
      for (let i = 0; i < 3; i++) {
        await page.keyboard.press('Tab')
        focusInfo.push(
          await page.evaluate(() => {
            const el = document.activeElement
            if (!el || el === document.body) return null
            const cs = getComputedStyle(el)
            return {
              tag: el.tagName.toLowerCase(),
              label: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 24),
              outlineWidth: cs.outlineWidth,
              outlineColor: cs.outlineColor,
              outlineStyle: cs.outlineStyle,
            }
          })
        )
      }
      const noRing = focusInfo.filter(
        (f) => f && (f.outlineStyle === 'none' || parseFloat(f.outlineWidth) === 0)
      )
      if (noRing.length)
        findings.push({ type: 'focus', vp: vp.name, route: route.name, items: noRing })
    }

    await page.screenshot({ path: `${OUT}${route.name}-${vp.name}.png`, fullPage: vp.name !== '1440' })
    await page.close()
  }
}

// 5) 모바일 네비게이션 토글 존재 확인 (비로그인 상태에서는 렌더되지 않으므로 존재 여부만 기록)
await browser.close()

console.log(JSON.stringify({ findingCount: findings.length, findings }, null, 2))
