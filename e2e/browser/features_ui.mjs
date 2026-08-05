/** 새 기능의 브라우저 동작 검증: 탭, 기간 필터, 목차 스크롤스파이, 플로팅 바, 업로드 UI. */
import puppeteer from 'puppeteer-core'
import fs from 'node:fs'
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)

const WEB = process.env.E2E_WEB || 'http://localhost:3001'
/*
 * 이 스크립트가 쓸 계정은 아래 시드 블록에서 직접 만든다.
 * 로컬에만 있는 계정에 기대면 CI 의 빈 DB 에서 로그인이 401 로 떨어진다.
 * EMAIL/PASS 를 주면 그 계정을 쓴다 (기존 계정으로 확인하고 싶을 때).
 */
const PASS = process.env.PASS || 'password1234'
const OUT = new URL('./shots/features', import.meta.url).pathname.replace(/^\//, '')
fs.mkdirSync(OUT, { recursive: true })

let ok = 0, fail = 0
const check = (name, cond, detail = '') => {
  if (cond) { ok++; console.log(`  PASS  ${name}`) }
  else { fail++; console.log(`  FAIL  ${name}  ${detail}`) }
}

/*
 * 썸네일 검증에 쓸 글을 직접 만든다.
 * DB 에 남아 있는 다른 테스트의 글에 기대면, 그 글이 지워지는 순간 여기가 깨진다.
 */
const API = (process.env.E2E_API || 'http://localhost:8001') + '/api/v1'
const seedStamp = String(process.pid) + String(Math.floor(Date.now() / 1000))
const api = async (method, path, body, token, raw) => {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { ...(raw ? {} : { 'Content-Type': 'application/json' }),
               ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : (raw ? body : JSON.stringify(body)),
  })
  const text = await res.text()
  try { return [res.status, JSON.parse(text || '{}')] } catch { return [res.status, text] }
}

const EMAIL = process.env.EMAIL || `thumb${seedStamp}@devshiplog.com`
const [, seedUser] = await api('POST', '/auth/register', {
  email: EMAIL, password: PASS, name: '썸네일',
})
const seedToken = seedUser.access_token
await api('PUT', '/profile/me', { handle: `thumb${seedStamp}` }, seedToken)

// 리사이즈본이 생기도록 충분히 큰 PNG 를 만든다.
const { createCanvas } = { createCanvas: null }
const bigPng = (() => {
  // 1600x900 단색 PNG 를 직접 조립한다 (외부 의존성 없이).
  const zlib = require('node:zlib')
  const W = 1600, H = 900
  const rows = Buffer.alloc((W * 3 + 1) * H)
  for (let y = 0; y < H; y++) {
    const off = y * (W * 3 + 1)
    rows[off] = 0
    for (let x = 0; x < W; x++) {
      rows[off + 1 + x * 3] = 60
      rows[off + 2 + x * 3] = 140
      rows[off + 3 + x * 3] = 200
    }
  }
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length)
    const body = Buffer.concat([Buffer.from(type), data])
    const crc = Buffer.alloc(4); crc.writeUInt32BE(zlib.crc32 ? zlib.crc32(body) >>> 0 : crc32(body))
    return Buffer.concat([len, body, crc])
  }
  function crc32(buf) {
    let c, crc = 0xffffffff
    for (let n = 0; n < buf.length; n++) {
      c = (crc ^ buf[n]) & 0xff
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
      crc = (crc >>> 8) ^ c
    }
    return (crc ^ 0xffffffff) >>> 0
  }
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4)
  ihdr[8] = 8; ihdr[9] = 2
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(rows)), chunk('IEND', Buffer.alloc(0)),
  ])
})()

const form = new FormData()
form.append('file', new Blob([bigPng], { type: 'image/png' }), 'cover.png')
const upRes = await fetch(`${API}/uploads/images`, {
  method: 'POST', headers: { Authorization: `Bearer ${seedToken}` }, body: form,
})
const uploaded = await upRes.json()

const [, seedSrc] = await api('POST', '/sources/extract', { raw_text: 'x' }, seedToken)
const [, seedDraft] = await api('POST', '/drafts', {
  source_ids: [seedSrc[0].id], type: 'implementation',
  audience: 'intermediate', length: 'default', use_style_profile: false,
}, seedToken)
await api('PUT', `/drafts/${seedDraft.id}/content`,
  { content_md: ['## 처음', '', '본문입니다. '.repeat(120), '', '## 중간', '', '본문입니다. '.repeat(120), '', '## 마지막', '', '본문입니다. '.repeat(120)].join(String.fromCharCode(10)) },
  seedToken)
await api('POST', '/posts', {
  draft_id: seedDraft.id, title: `썸네일 검증 ${seedStamp}`, cover_url: uploaded.url,
}, seedToken)
await new Promise((r) => setTimeout(r, 3000)) // 캐시 무효화 대기

const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH ||
  'C:/Users/vrsoft/.cache/puppeteer/chrome/win64-151.0.7922.47/chrome-win64/chrome.exe', headless: 'shell', args: ['--no-sandbox'] })
const page = await browser.newPage()
await page.setViewport({ width: 1440, height: 960 })
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('response', (r) => { if (r.status() >= 400) errors.push(`HTTP ${r.status()} ${r.url()}`) })
// 저장소를 바꾸기 전에 올라간 옛 파일들은 이 실행의 관심사가 아니다.
const isLegacyAsset = (m) => m.includes('/uploads/')

const shot = async (name) => page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false })
const setTheme = async (t) => {
  await page.evaluate((theme) => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, t)
  await new Promise((r) => setTimeout(r, 200))
}

console.log('='.repeat(68))
console.log('1. 홈 탭 + 기간 필터')
console.log('='.repeat(68))

for (const [q, label] of [['', '최신'], ['?sort=trending', '트렌딩'], ['?sort=recommended', '추천'], ['?sort=following', '피드']]) {
  await page.goto(`${WEB}/${q}`, { waitUntil: 'networkidle0' })
  const active = await page.$eval('nav[aria-label="정렬"] [aria-current="page"]', (el) => el.textContent.trim())
  check(`${label} 탭이 활성 표시됨`, active === label, active)
}

await page.goto(`${WEB}/?sort=trending`, { waitUntil: 'networkidle0' })
check('트렌딩에 기간 필터 보임', await page.$('[aria-label="기간"]') !== null)
await page.click('[aria-label="기간"] a:nth-child(3)')
await page.waitForNavigation({ waitUntil: 'networkidle0' })
check('기간 클릭이 URL 에 반영', page.url().includes('period=year'), page.url())
const yearActive = await page.$eval('[aria-label="기간"] [aria-current="true"]', (el) => el.textContent.trim())
check('선택한 기간이 활성 표시', yearActive === '올해', yearActive)
await shot('home-trending-light')
await setTheme('dark'); await shot('home-trending-dark'); await setTheme('light')

await page.goto(`${WEB}/`, { waitUntil: 'networkidle0' })
check('최신 탭엔 기간 필터 없음', await page.$('[aria-label="기간"]') === null)
// 방금 시드한 글의 썸네일만 본다. DB 에 남아 있는 다른 글의 이미지는 대상이 아니다.
const thumbs = await page.$$eval('article img', (els) =>
  els.filter((e) => e.getAttribute('src')?.includes('/posts/')).map((e) => e.naturalWidth))
check('카드 썸네일이 실제로 로드됨', thumbs.length > 0 && thumbs.some((w) => w > 0), JSON.stringify(thumbs))
await shot('home-recent-light')

console.log('')
console.log('='.repeat(68))
console.log('2. 글 페이지 — 목차 + 플로팅 바')
console.log('='.repeat(68))

// 목차가 2개 이상인 글을 홈에서 찾는다.
const postHref = await page.$$eval('article h2', (els) => els.map((e) => e.closest('a')?.getAttribute('href')).filter(Boolean))
let target = null
for (const href of postHref) {
  await page.goto(`${WEB}${href}`, { waitUntil: 'networkidle0' })
  if (await page.$('nav[aria-label="목차"]')) { target = href; break }
}
check('목차가 있는 글을 찾음', target !== null, String(postHref.length))

if (target) {
  const items = await page.$$eval('nav[aria-label="목차"] a', (els) => els.map((e) => e.getAttribute('href')))
  check('목차 항목 2개 이상', items.length >= 2, String(items.length))

  const anchorsResolve = await page.evaluate((hrefs) =>
    hrefs.every((h) => document.getElementById(decodeURIComponent(h.slice(1))) !== null), items)
  check('모든 목차 링크가 실제 제목을 가리킴', anchorsResolve)

  check('처음엔 플로팅 바 숨김', await page.$eval('[aria-label="좋아요"], [aria-label="좋아요 취소"]',
    (el) => el.closest('div[aria-hidden]').getAttribute('aria-hidden')) === 'true')

  // 마지막 제목으로 스크롤 → 스크롤스파이가 따라오는지
  await page.evaluate((id) => document.getElementById(id)?.scrollIntoView(), decodeURIComponent(items[items.length - 1].slice(1)))
  await new Promise((r) => setTimeout(r, 700))
  const current = await page.$eval('nav[aria-label="목차"] [aria-current="location"]', (el) => el.getAttribute('href')).catch(() => null)
  check('스크롤하면 현재 항목이 바뀜', current === items[items.length - 1], `${current} vs ${items[items.length - 1]}`)

  check('스크롤 후 플로팅 바 노출', await page.$eval('[aria-label="좋아요"], [aria-label="좋아요 취소"]',
    (el) => el.closest('div[aria-hidden]').getAttribute('aria-hidden')) === 'false')

  const box = await page.$eval('nav[aria-label="목차"]', (el) => {
    const r = el.getBoundingClientRect()
    return { left: r.left, right: r.right, w: window.innerWidth }
  })
  check('목차가 화면 안에 있음', box.left >= 0 && box.right <= box.w, JSON.stringify(box))

  const fb = await page.$eval('[aria-label="주소 공유"]', (el) => {
    const r = el.closest('div[aria-hidden]').getBoundingClientRect()
    const c = document.querySelector('article, main .prose')?.getBoundingClientRect()
    return { right: r.right, contentLeft: c ? c.left : null }
  })
  check('플로팅 바가 본문을 가리지 않음', fb.contentLeft === null || fb.right <= fb.contentLeft + 8, JSON.stringify(fb))

  await shot('post-toc-light')
  await setTheme('dark'); await shot('post-toc-dark'); await setTheme('light')

  // 좁은 화면에서는 목차/플로팅 바가 사라져야 한다
  await page.setViewport({ width: 390, height: 844 })
  await new Promise((r) => setTimeout(r, 400))
  const hiddenOnMobile = await page.evaluate(() => {
    const toc = document.querySelector('nav[aria-label="목차"]')
    const fbar = document.querySelector('[aria-label="주소 공유"]')?.closest('div[aria-hidden]')
    const vis = (el) => el && el.getBoundingClientRect().width > 0
    return { toc: vis(toc), fbar: vis(fbar) }
  })
  check('모바일에서 목차 숨김', !hiddenOnMobile.toc, JSON.stringify(hiddenOnMobile))
  check('모바일에서 플로팅 바 숨김', !hiddenOnMobile.fbar, JSON.stringify(hiddenOnMobile))
  const hScroll = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  check('모바일 가로 스크롤 없음', hScroll <= 1, String(hScroll))
  await shot('post-mobile')
  await page.setViewport({ width: 1440, height: 960 })
}

console.log('')
console.log('='.repeat(68))
console.log('3. 업로드 UI (로그인 필요)')
console.log('='.repeat(68))

await page.goto(`${WEB}/auth/login`, { waitUntil: 'networkidle0' })
await page.type('input[type="email"]', EMAIL)
await page.type('input[type="password"]', PASS)
await Promise.all([
  page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {}),
  page.click('button[type="submit"]'),
])
check('로그인 성공', !page.url().includes('/auth/login'), page.url())

await page.goto(`${WEB}/settings`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('input[type="file"]', { timeout: 30000 }).catch(() => {})
const fileInput = await page.$('input[type="file"]')
check('설정에 아바타 업로드 입력 있음', fileInput !== null)

if (fileInput) {
  const png = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=',
    'base64')
  const tmp = `${OUT}/avatar.png`
  fs.writeFileSync(tmp, png)
  await fileInput.uploadFile(tmp)
  await new Promise((r) => setTimeout(r, 2500))
  const avatarSrc = await page.$$eval('img', (els) => els.map((e) => e.src).find((s) => s.includes('/avatars/')) ?? null)
  check('아바타가 미리보기에 반영됨', avatarSrc !== null, String(avatarSrc))
  await shot('settings-avatar')
}

const relevant = errors.filter((e) => !isLegacyAsset(e))
check('콘솔 에러 없음', relevant.length === 0, relevant.slice(0, 3).join(' | '))

console.log('')
console.log('='.repeat(68))
console.log(`결과: ${ok} PASS / ${fail} FAIL`)
console.log('='.repeat(68))
await browser.close()
process.exit(fail ? 1 : 0)
