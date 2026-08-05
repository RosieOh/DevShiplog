/** 개선 항목 브라우저 검증: 에디터 붙여넣기 업로드, 충돌 배너, 시리즈 네비, 하이라이팅, 재설정. */
import puppeteer from 'puppeteer-core'
import fs from 'node:fs'
import { execFileSync } from 'node:child_process'

// 같은 IP 에서 반복 실행되므로 레이트리밋 카운터를 비운다. 안 그러면 두 번째
// 실행부터 429 가 나서 실제 화면 동작을 못 본다.
try {
  execFileSync('docker', ['exec', 'devshiplog-redis', 'sh', '-c',
    "redis-cli --scan --pattern 'rl:*' | xargs -r redis-cli del"], { stdio: 'ignore' })
} catch { /* Redis 가 없으면 레이트리밋 자체가 꺼져 있다 */ }

const CHROME =
  process.env.CHROME_PATH ||
  'C:/Users/vrsoft/.cache/puppeteer/chrome/win64-151.0.7922.47/chrome-win64/chrome.exe'
const WEB = process.env.E2E_WEB || 'http://localhost:3001'
const API = (process.env.E2E_API || 'http://localhost:8001') + '/api/v1'
const OUT = new URL('./shots/improve', import.meta.url).pathname.replace(/^\//, '')
fs.mkdirSync(OUT, { recursive: true })

let ok = 0, fail = 0
const check = (name, cond, detail = '') => {
  if (cond) { ok++; console.log(`  PASS  ${name}`) }
  else { fail++; console.log(`  FAIL  ${name}  ${detail}`) }
}

const stamp = String(Math.floor(Number(process.env.STAMP || '0') || 1)) + String(process.pid)
const EMAIL = `ui${stamp}@devshiplog.com`
const PASSWORD = 'password1234'

const api = async (method, path, body, token) => {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const text = await res.text()
  try { return [res.status, JSON.parse(text || '{}')] } catch { return [res.status, text] }
}

// --- 계정과 글 준비 -------------------------------------------------------
const [, reg] = await api('POST', '/auth/register', {
  email: EMAIL, password: PASSWORD, name: '개선UI',
})
const token = reg.access_token
await api('PUT', '/profile/me', { handle: `ui${stamp}`, display_name: '개선UI' }, token)

const makeDraft = async (bodyMd) => {
  const [, src] = await api('POST', '/sources/extract', { raw_text: 'x' }, token)
  const [, draft] = await api('POST', '/drafts', {
    source_ids: [src[0].id], type: 'implementation',
    audience: 'intermediate', length: 'default', use_style_profile: false,
  }, token)
  await api('PUT', `/drafts/${draft.id}/content`, { content_md: bodyMd }, token)
  return draft
}

const CODE_BODY = `## 배경

아래는 파이썬 코드입니다.

\`\`\`python
def hello(name):
    return f"Hello, {name}"
\`\`\`

## 정리

설명이 이어집니다. 발행 최소 길이를 넘기기 위해 조금 더 적습니다.
`
const codeDraft = await makeDraft(CODE_BODY)
const [, codePost] = await api('POST', '/posts', {
  draft_id: codeDraft.id, title: `코드 ${stamp}`, tags: ['Python'],
}, token)

const [, series] = await api('POST', '/series', { name: `연재 ${stamp}` }, token)
const seriesPosts = []
for (let i = 1; i <= 3; i++) {
  const d = await makeDraft(`## ${i}편\n\n내용입니다. `.repeat(6))
  const [, p] = await api('POST', '/posts', { draft_id: d.id, title: `${i}편 ${stamp}` }, token)
  await api('POST', `/series/${series.id}/posts`, { post_id: p.id }, token)
  seriesPosts.push(p)
}

const editorDraft = await makeDraft('편집기 검증용 초안입니다. '.repeat(6))

await new Promise((r) => setTimeout(r, 2500)) // 캐시 무효화 대기

// --- 브라우저 -------------------------------------------------------------
const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'shell', args: ['--no-sandbox'],
})
const page = await browser.newPage()
await page.setViewport({ width: 1440, height: 960 })
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })

const shot = (name) => page.screenshot({ path: `${OUT}/${name}.png` })
const setTheme = async (t) => {
  await page.evaluate((theme) => document.documentElement.setAttribute('data-theme', theme), t)
  await new Promise((r) => setTimeout(r, 200))
}

console.log('='.repeat(68))
console.log('1. 코드 하이라이팅')
console.log('='.repeat(68))

await page.goto(`${WEB}/@ui${stamp}/${encodeURIComponent(codePost.slug)}`, {
  waitUntil: 'networkidle0',
})
check('코드 블록에 hljs', (await page.$('pre code.hljs')) !== null)
const tokenColors = await page.$$eval('pre code .hljs-keyword, pre code .hljs-string', (els) =>
  els.map((e) => getComputedStyle(e).color)
)
check('토큰마다 색이 다르다', new Set(tokenColors).size > 1, JSON.stringify(tokenColors))

// 코드 배경 위에서 토큰 대비가 4.5:1 이상인지
const contrast = await page.evaluate(() => {
  const lum = ([r, g, b]) => {
    const f = (c) => {
      const s = c / 255
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
    }
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
  }
  const parse = (s) => (s.match(/\d+(\.\d+)?/g) || []).slice(0, 3).map(Number)
  const pre = document.querySelector('pre')
  const bg = parse(getComputedStyle(pre).backgroundColor)
  const worst = []
  for (const el of pre.querySelectorAll('[class^="hljs-"]')) {
    const fg = parse(getComputedStyle(el).color)
    const [hi, lo] = lum(fg) > lum(bg) ? [lum(fg), lum(bg)] : [lum(bg), lum(fg)]
    worst.push({ cls: el.className, ratio: +((hi + 0.05) / (lo + 0.05)).toFixed(2) })
  }
  return worst.sort((a, b) => a.ratio - b.ratio)[0] ?? null
})
check('가장 낮은 토큰 대비도 4.5:1 이상', !contrast || contrast.ratio >= 4.5, JSON.stringify(contrast))
await shot('code-light')
await setTheme('dark'); await shot('code-dark'); await setTheme('light')

console.log('')
console.log('='.repeat(68))
console.log('2. 시리즈 네비게이션')
console.log('='.repeat(68))

await page.goto(`${WEB}/@ui${stamp}/${encodeURIComponent(seriesPosts[1].slug)}`, {
  waitUntil: 'networkidle0',
})
const navs = await page.$$('nav[aria-label="시리즈"]')
check('본문 앞뒤에 시리즈 네비 2개', navs.length === 2, String(navs.length))

const navText = await page.$eval('nav[aria-label="시리즈"]', (el) => el.textContent)
check('현재 위치 표시 (2 / 3)', navText.includes('2') && navText.includes('3'), navText.slice(0, 60))

const links = await page.$$eval('nav[aria-label="시리즈"] a', (els) =>
  els.map((e) => ({ text: e.textContent.trim(), href: e.getAttribute('href') }))
)
check('이전 글 링크 존재', links.some((l) => l.text.includes('이전 글')), JSON.stringify(links))
check('다음 글 링크 존재', links.some((l) => l.text.includes('다음 글')), JSON.stringify(links))

// 실제로 이동되는지
const nextHref = links.find((l) => l.text.includes('다음 글')).href
await page.goto(`${WEB}${nextHref}`, { waitUntil: 'networkidle0' })
const movedTitle = await page.$eval('h1', (el) => el.textContent.trim())
check('다음 글로 실제 이동', movedTitle.startsWith('3편'), movedTitle)
const lastNav = await page.$eval('nav[aria-label="시리즈"]', (el) => el.textContent)
check('마지막 편에는 다음 글이 없다', !lastNav.includes('다음 글'), lastNav.slice(0, 80))
await shot('series-light')
await setTheme('dark'); await shot('series-dark'); await setTheme('light')

console.log('')
console.log('='.repeat(68))
console.log('3. 비밀번호 재설정 화면')
console.log('='.repeat(68))

await page.goto(`${WEB}/auth/login`, { waitUntil: 'networkidle0' })
check('로그인에 비밀번호 찾기 링크', (await page.$('a[href="/auth/forgot"]')) !== null)

await page.goto(`${WEB}/auth/forgot`, { waitUntil: 'networkidle0' })
await page.type('input[type="email"]', EMAIL)
await page.click('button[type="submit"]')
await page.waitForFunction(() => document.body.textContent.includes('메일함'), { timeout: 15000 })
check('요청 후 안내 문구 표시', true)
await shot('forgot')

await page.goto(`${WEB}/auth/reset`, { waitUntil: 'networkidle0' })
check('토큰 없으면 안내 표시', (await page.$eval('body', (b) => b.textContent)).includes('잘못된 링크'))

await page.goto(`${WEB}/auth/reset?token=${'x'.repeat(40)}`, { waitUntil: 'networkidle0' })
await page.type('#password', 'short')
const shortWarn = await page.$eval('body', (b) => b.textContent)
check('짧은 비밀번호를 즉시 알려준다', shortWarn.includes('8자 이상'), '')
await page.$eval('#password', (el) => { el.value = '' })
await page.type('#password', 'longenough1234')
await page.type('#confirm', 'different1234')
check('불일치를 즉시 알려준다',
  (await page.$eval('body', (b) => b.textContent)).includes('두 비밀번호가 다릅니다'))
await shot('reset')

console.log('')
console.log('='.repeat(68))
console.log('4. 에디터 — 붙여넣기 업로드 + 충돌')
console.log('='.repeat(68))

await page.goto(`${WEB}/auth/login`, { waitUntil: 'networkidle0' })
await page.type('input[type="email"]', EMAIL)
await page.type('input[type="password"]', PASSWORD)
await Promise.all([
  page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {}),
  page.click('button[type="submit"]'),
])
check('로그인', !page.url().includes('/auth/login'), page.url())

await page.goto(`${WEB}/drafts/${editorDraft.id}/edit`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('textarea[aria-label="마크다운 편집기"]', { timeout: 30000 })
const editor = await page.$('textarea[aria-label="마크다운 편집기"]')
check('마크다운 편집기 렌더링', editor !== null)
check('업로드 안내 문구 노출',
  (await page.$eval('body', (b) => b.textContent)).includes('끌어다 놓으면'))

// 붙여넣기로 이미지 업로드
await page.evaluate(() => {
  const el = document.querySelector('textarea[aria-label="마크다운 편집기"]')
  el.focus()
  el.setSelectionRange(el.value.length, el.value.length)
  // 1x1 PNG
  const b64 =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
  const file = new File([bytes], 'pasted.png', { type: 'image/png' })
  const dt = new DataTransfer()
  dt.items.add(file)
  el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }))
})
await page.waitForFunction(
  () => document.querySelector('textarea[aria-label="마크다운 편집기"]')?.value.includes('/uploads/'),
  { timeout: 20000 }
).catch(() => {})
const editorValue = await page.$eval('textarea[aria-label="마크다운 편집기"]', (el) => el.value)
check('붙여넣은 이미지가 업로드되어 마크다운으로 삽입됨',
  /!\[pasted\]\(\S+\.png\)/.test(editorValue), editorValue.slice(-90))
check('자리표시자가 남지 않음', !editorValue.includes('업로드 중'), editorValue.slice(-90))

await page.waitForFunction(
  () => document.querySelector('.prose img') !== null, { timeout: 10000 }
).catch(() => {})
check('미리보기에도 이미지가 반영됨', (await page.$('.prose img')) !== null)
await shot('editor')

// 충돌: 다른 곳(API)에서 먼저 저장한 뒤 편집기에서 타이핑
await page.waitForFunction(() => !document.body.textContent.includes('저장 중'), { timeout: 10000 })
  .catch(() => {})
await api('PUT', `/drafts/${editorDraft.id}/content`,
  { content_md: '다른 탭에서 쓴 내용입니다. '.repeat(5) }, token)

await page.focus('textarea[aria-label="마크다운 편집기"]')
await page.type('textarea[aria-label="마크다운 편집기"]', '\n여기서 계속 씁니다.')
await page.waitForFunction(() => document.querySelector('[role="alert"]') !== null, { timeout: 15000 })
  .catch(() => {})
const banner = await page.$('[role="alert"]')
check('충돌 배너가 뜬다', banner !== null)
if (banner) {
  const text = await page.$eval('[role="alert"]', (el) => el.textContent)
  check('덮어쓰기 / 불러오기 선택지 제공',
    text.includes('덮어쓰기') && text.includes('불러오기'), text.slice(0, 80))
  await shot('conflict')

  await page.evaluate(() => {
    const buttons = [...document.querySelectorAll('[role="alert"] button')]
    buttons.find((b) => b.textContent.includes('저쪽 내용 불러오기'))?.click()
  })
  await new Promise((r) => setTimeout(r, 800))
  const after = await page.$eval('textarea[aria-label="마크다운 편집기"]', (el) => el.value)
  check('불러오기가 저쪽 내용으로 교체한다', after.includes('다른 탭에서 쓴 내용'), after.slice(0, 60))
  check('배너가 닫힌다', (await page.$('[role="alert"]')) === null)
}

console.log('')
console.log('='.repeat(68))
console.log('5. 접근성 / 반응형')
console.log('='.repeat(68))

await page.goto(`${WEB}/@ui${stamp}/${encodeURIComponent(seriesPosts[1].slug)}`, {
  waitUntil: 'domcontentloaded',
})
await page.waitForSelector('nav[aria-label="시리즈"]', { timeout: 30000 })
for (const [w, h, label] of [[390, 844, '모바일'], [768, 1024, '태블릿'], [1440, 960, '데스크톱']]) {
  await page.setViewport({ width: w, height: h })
  await new Promise((r) => setTimeout(r, 400))
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  )
  check(`${label} 가로 스크롤 없음`, overflow <= 1, String(overflow))
  const small = await page.$$eval('nav[aria-label="시리즈"] a', (els) =>
    els.filter((e) => e.getBoundingClientRect().height < 44).map((e) => e.textContent.trim())
  )
  check(`${label} 시리즈 링크 터치 타깃 44px`, small.length === 0, JSON.stringify(small))
}
await page.setViewport({ width: 390, height: 844 })
await shot('series-mobile')

/*
 * 충돌 시나리오에서 브라우저가 409 응답을 콘솔에 남긴다. 우리가 일부러 낸 것이라
 * 오류가 아니다 (앱은 배너로 처리한다). 그 외의 에러는 없어야 한다.
 */
const unexpected = errors.filter((e) => !e.includes('409'))
check('예상치 못한 콘솔 에러 없음', unexpected.length === 0, unexpected.slice(0, 3).join(' | '))

console.log('')
console.log('='.repeat(68))
console.log(`결과: ${ok} PASS / ${fail} FAIL`)
console.log('='.repeat(68))
await browser.close()
process.exit(fail ? 1 : 0)
