import type { Metadata } from 'next'
import Link from 'next/link'
import { SITE_NAME, SITE_URL } from '@/lib/api/public'

export const metadata: Metadata = {
  title: `${SITE_NAME} — 낡지 않는 기술 블로그`,
  description:
    '기술 글은 시간이 지나면 틀린 글이 됩니다. Devshiplog 는 글이 어떤 스택의 어떤 버전에서 언제 확인됐는지를 기록하고, 낡으면 알려줍니다.',
  alternates: { canonical: `${SITE_URL}/about` },
}

/**
 * 소개 페이지.
 *
 * "AI 로 글을 써드립니다" 로 시작하지 않는다. 그건 이제 흔한 말이고,
 * 우리가 실제로 해결하는 문제도 아니다. 문제부터 말한다.
 */

const STEPS = [
  {
    step: '01',
    title: '쓴다',
    body: 'URL·로그·PR 을 넣으면 초안이 나옵니다. 전에 쓴 글에서 문체를 배워 내 말투로 씁니다.',
  },
  {
    step: '02',
    title: '전제를 남긴다',
    body: '본문에서 기술과 버전을 자동으로 찾아냅니다. 확인만 하고 발행하면 됩니다.',
  },
  {
    step: '03',
    title: '확인한다',
    body: '다시 돌려보고 “지금도 된다”를 누릅니다. 글을 고치지 않아도 됩니다.',
  },
  {
    step: '04',
    title: '알림을 받는다',
    body: '버전이 올라가거나 독자가 “안 됐어요”를 누르면 갱신 목록에 올라옵니다.',
  },
]

const COMPARISON: [string, string, string][] = [
  ['글의 전제', '안 적혀 있음', 'react@18.3 · node@20 으로 구조화'],
  ['신뢰도', '작성 날짜 한 줄', '마지막 검증 시각 + 스택 최신성'],
  ['낡은 글', '방치', '독자에게 경고, 작성자에게 갱신 목록'],
  ['“안 돼요”', '댓글에 묻힘', '구조화된 신호 → 작성자 대시보드'],
  ['탐색', '태그 (자유 문자열)', '스택 + 버전 (정규화)'],
]

const LEVELS = [
  { dot: 'bg-fresh', text: 'text-fresh', label: '검증됨', hint: '6개월 안에 확인' },
  { dot: 'bg-aging', text: 'text-aging', label: '확인 필요', hint: '확인이 오래됨' },
  { dot: 'bg-stale', text: 'text-stale', label: '오래됨', hint: '메이저 버전이 지남' },
  { dot: 'bg-ink-faint', text: 'text-ink-faint', label: '미검증', hint: '확인 이력 없음' },
]

export default function AboutPage() {
  return (
    <div className="bg-bg">
      {/* ── 문제 ─────────────────────────────────────────────── */}
      <section className="mx-auto max-w-shell px-4 pb-16 pt-20 md:px-6 md:pt-28">
        <p className="font-mono text-xs uppercase tracking-widest text-ink-faint">
          개발 블로그 플랫폼
        </p>

        <h1 className="mt-4 max-w-4xl text-[clamp(2rem,5.5vw,4rem)] font-bold leading-[1.15] tracking-tight text-ink text-balance">
          기술 글은 시간이 지나면
          <br />
          <span className="text-stale">틀린 글</span>이 됩니다.
        </h1>

        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink-muted">
          검색해서 나온 글을 따라 했는데 안 됩니다. 스크롤을 올려 날짜를 봅니다.
          <span className="whitespace-nowrap"> 2023년.</span> 어느 버전 기준인지는 안 적혀
          있습니다. 댓글에 “저도 안 돼요”가 셋 달려 있고 답이 없습니다.
        </p>

        <p className="mt-4 max-w-2xl text-lg leading-relaxed text-ink">
          <b className="font-bold">읽는 사람</b>은 그 글을 믿어도 되는지 알 수 없고,
          <b className="font-bold"> 쓴 사람</b>은 자기 글이 낡은 걸 모릅니다.
        </p>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            href="/drafts/new"
            className="inline-flex min-h-touch items-center rounded bg-ink px-7 text-sm font-bold text-bg transition-opacity hover:opacity-85"
          >
            글 쓰기
          </Link>
          <Link
            href="/"
            className="inline-flex min-h-touch items-center rounded border border-border bg-surface px-7 text-sm font-bold text-ink transition-colors hover:bg-surface-2"
          >
            글 둘러보기
          </Link>
        </div>
      </section>

      {/* ── 우리가 다르게 하는 것 ──────────────────────────────── */}
      <section className="border-y border-border bg-surface">
        <div className="mx-auto max-w-shell px-4 py-16 md:px-6 md:py-20">
          <h2 className="text-2xl font-bold tracking-tight text-ink md:text-3xl">
            그래서 <span className="text-accent-text">낡음</span>을 기능으로 다룹니다.
          </h2>
          <p className="mt-4 max-w-2xl leading-relaxed text-ink-muted">
            글을 텍스트 덩어리가 아니라{' '}
            <b className="font-bold text-ink">
              “어떤 스택의 어떤 버전에서, 언제 확인된 절차”
            </b>
            로 다룹니다. 그렇게 다루면 할 수 있는 일이 생깁니다.
          </p>

          {/* 표는 좁은 화면에서 가로로 넘친다. 페이지가 아니라 표만 스크롤되게 한다. */}
          <div className="mt-10 overflow-x-auto">
            <table className="w-full min-w-[36rem] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th scope="col" className="py-3 pr-4 font-semibold text-ink-faint">
                    <span className="sr-only">항목</span>
                  </th>
                  <th scope="col" className="py-3 pr-4 font-semibold text-ink-faint">
                    보통의 블로그
                  </th>
                  <th scope="col" className="py-3 font-semibold text-ink">
                    Devshiplog
                  </th>
                </tr>
              </thead>
              <tbody className="text-ink-muted">
                {COMPARISON.map(([label, before, after]) => (
                  <tr key={label} className="border-b border-border-subtle">
                    <th scope="row" className="py-3 pr-4 text-left font-medium text-ink">
                      {label}
                    </th>
                    <td className="py-3 pr-4">{before}</td>
                    <td className="py-3 font-medium text-ink">{after}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── 어떻게 쓰는가 ────────────────────────────────────── */}
      <section className="mx-auto max-w-shell px-4 py-16 md:px-6 md:py-20">
        <h2 className="text-2xl font-bold tracking-tight text-ink md:text-3xl">쓰는 흐름</h2>

        <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((item) => (
            <li key={item.step} className="rounded border border-border bg-surface p-5">
              <span className="font-mono text-xs tabular-nums text-accent-text">{item.step}</span>
              <h3 className="mt-3 text-base font-bold text-ink">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{item.body}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ── 신선도 어휘 ──────────────────────────────────────── */}
      <section className="border-t border-border bg-surface">
        <div className="mx-auto max-w-shell px-4 py-16 md:px-6 md:py-20">
          <h2 className="text-2xl font-bold tracking-tight text-ink md:text-3xl">
            글마다 상태가 붙습니다
          </h2>
          <p className="mt-3 max-w-2xl leading-relaxed text-ink-muted">
            작성일이 아니라 <b className="font-bold text-ink">마지막으로 동작을 확인한 시각</b>{' '}
            기준입니다. 2년 전 글도 어제 다시 돌려봤다면 믿을 수 있고, 어제 쓴 글도 이미
            틀렸을 수 있습니다.
          </p>

          <ul className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {LEVELS.map((level) => (
              <li key={level.label} className="rounded border border-border bg-bg p-4">
                <span className="inline-flex items-center gap-2">
                  <span aria-hidden="true" className={`h-2 w-2 rounded-full ${level.dot}`} />
                  <span className={`text-sm font-bold ${level.text}`}>{level.label}</span>
                </span>
                <p className="mt-1.5 text-xs text-ink-muted">{level.hint}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── 닫기 ─────────────────────────────────────────────── */}
      <section className="mx-auto max-w-shell px-4 py-16 text-center md:px-6 md:py-24">
        <h2 className="text-2xl font-bold tracking-tight text-ink text-balance md:text-3xl">
          쓴 글이 계속 맞는 글로 남게
        </h2>
        <p className="mx-auto mt-4 max-w-xl leading-relaxed text-ink-muted">
          개인 블로그는 무료입니다. 주소는{' '}
          <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-sm text-ink">
            devshiplog.com/@아이디
          </code>{' '}
          입니다.
        </p>
        <Link
          href="/auth/login"
          className="mt-8 inline-flex min-h-touch items-center rounded bg-ink px-8 text-sm font-bold text-bg transition-opacity hover:opacity-85"
        >
          시작하기
        </Link>
      </section>
    </div>
  )
}
