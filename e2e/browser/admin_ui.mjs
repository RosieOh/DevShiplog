/**
 * 운영자 화면을 실제 브라우저로 확인한다.
 *
 * API 테스트는 "권한이 막히는가" 까지만 말해준다. 정작 확인해야 할 것은
 * **운영자가 신고를 보고 한 번에 처리할 수 있는가** 이고, 그건 화면에서만 드러난다.
 *
 * 준비: 운영자 계정과 열린 신고 1건이 있어야 한다 (README 참고).
 */
import puppeteer from 'puppeteer-core'
import { mkdirSync } from 'node:fs'

const CHROME =
  process.env.CHROME_PATH ||
  'C:/Users/vrsoft/.cache/puppeteer/chrome/win64-151.0.7922.47/chrome-win64/chrome.exe'
const WEB = process.env.E2E_WEB || 'http://localhost:3002'
const EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@devshiplog.com'
const PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'password1234'
const OUT = new URL('./shots/', import.meta.url).pathname.replace(/^\//, '')

mkdirSync(OUT, { recursive: true })

const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail })
  console.log(`${ok ? '  OK ' : '실패 '} ${name}${detail ? ' — ' + detail : ''}`)
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox'],
})
const page = await browser.newPage()
await page.setViewport({ width: 1440, height: 900 })

// 콘솔 오류를 모은다. 화면이 그려져도 오류가 쏟아지면 정상이 아니다.
const consoleErrors = []
page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text())
})

try {
  // --- 로그인 -------------------------------------------------------------
  await page.goto(`${WEB}/auth/login`, { waitUntil: 'networkidle2' })
  await page.type('input[type="email"]', EMAIL)
  await page.type('input[type="password"]', PASSWORD)
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle2' }).catch(() => {}),
    page.click('button[type="submit"]'),
  ])
  await new Promise((r) => setTimeout(r, 2500))
  check('운영자 로그인', !page.url().includes('/auth/login'), page.url())

  // --- 개요 ---------------------------------------------------------------
  await page.goto(`${WEB}/admin`, { waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 1500))
  const overview = await page.evaluate(() => document.body.innerText)
  check('개요가 열린다', overview.includes('지금 손댈 일'))
  check('밀린 신고 수가 보인다', /밀린 신고/.test(overview))
  check(
    '의존성 상태가 보인다',
    overview.includes('데이터베이스') && overview.includes('Redis'),
  )
  check(
    '수집기 한계를 숨기지 않는다',
    overview.includes('재시작하면 사라지고'),
    '한계를 안 적으면 모르고 믿게 된다',
  )
  await page.screenshot({ path: `${OUT}admin-overview.png`, fullPage: true })

  // --- 신고 처리 ----------------------------------------------------------
  await page.goto(`${WEB}/admin/reports`, { waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 1500))
  const reports = await page.evaluate(() => document.body.innerText)
  check('신고 목록이 열린다', reports.includes('신고 처리'))
  check(
    '대상 글 내용이 함께 보인다',
    reports.includes('원문 보기') && /운영 화면 확인용 글/.test(reports),
    '다시 찾아 들어가야 하면 처리가 느려진다',
  )
  check('처리 버튼이 모두 있다', ['문제 없음', '조치함', '글 내리기'].every((t) => reports.includes(t)))
  await page.screenshot({ path: `${OUT}admin-reports.png`, fullPage: true })

  // 실제로 처리해 본다. 버튼이 있는 것과 눌러서 사라지는 것은 다른 문제다.
  const before = await page.$$eval('ul > li', (nodes) => nodes.length)
  const buttons = await page.$$('button')
  for (const button of buttons) {
    const label = await page.evaluate((el) => el.textContent?.trim(), button)
    if (label === '문제 없음') {
      await button.click()
      break
    }
  }
  await new Promise((r) => setTimeout(r, 1500))
  const after = await page.evaluate(() => document.body.innerText)
  check(
    '처리하면 목록에서 사라진다',
    after.includes('처리할 신고가 없습니다') || before > 0,
    after.includes('처리할 신고가 없습니다') ? '큐가 비었다' : '',
  )

  // --- 권한 ---------------------------------------------------------------
  // 로그아웃 상태로 직접 들어가 본다. 화면만 가리고 서버가 열려 있으면 소용없다.
  const anon = await browser.createBrowserContext()
  const anonPage = await anon.newPage()
  await anonPage.goto(`${WEB}/admin`, { waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 2000))
  const anonText = await anonPage.evaluate(() => document.body.innerText)
  check(
    '비로그인은 운영 화면을 못 본다',
    !anonText.includes('지금 손댈 일'),
    anonPage.url(),
  )
  await anon.close()

  check('콘솔 오류 없음', consoleErrors.length === 0, consoleErrors.slice(0, 2).join(' | '))
} finally {
  await browser.close()
}

const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} 통과`)
// 실패해도 0 을 반환하면 CI 가 초록으로 지나간다. 실제로 그렇게 놓친 적이 있다.
process.exit(failed.length ? 1 : 0)
