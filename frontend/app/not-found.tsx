import Link from 'next/link'

/**
 * 404.
 *
 * 색을 하드코딩하지 않는다. 이전 버전은 `#d1fb52` 를 흰 배경에 얹어 대비가
 * 1.13:1 이었다 — 사실상 안 보인다. 배경도 고정이라 다크 모드에서 어긋났다.
 * 토큰을 쓰면 두 문제가 같이 사라진다.
 *
 * 'use client' 도 뺐다. 상호작용이 없으므로 서버에서 그리면 된다.
 */
export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-shell flex-col justify-center px-4 py-16 md:px-6">
      <p className="font-mono text-sm font-bold tracking-widest text-accent-text">404</p>
      <h1 className="mt-3 text-3xl font-bold tracking-tight text-ink md:text-4xl">
        페이지를 찾을 수 없습니다
      </h1>
      <p className="mt-3 max-w-xl leading-relaxed text-ink-muted">
        주소가 바뀌었거나, 글이 비공개로 바뀌었을 수 있습니다.
      </p>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/"
          className="inline-flex min-h-touch items-center rounded bg-ink px-6 text-sm font-bold text-bg transition-opacity hover:opacity-85"
        >
          글 둘러보기
        </Link>
        <Link
          href="/dashboard"
          className="inline-flex min-h-touch items-center rounded border border-border bg-surface px-6 text-sm font-bold text-ink transition-colors hover:bg-surface-2"
        >
          내 글로 가기
        </Link>
      </div>
    </div>
  )
}
