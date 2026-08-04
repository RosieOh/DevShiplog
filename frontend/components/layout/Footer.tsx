import Link from 'next/link'

export default function Footer() {
  // 하드코딩된 연도는 해가 바뀌면 바로 낡는다.
  const year = new Date().getFullYear()

  return (
    <footer className="mt-16 border-t border-border">
      <div className="mx-auto flex max-w-shell flex-col items-center justify-between gap-3 px-4 py-10 text-sm text-ink-faint md:flex-row md:px-6">
        <p>© {year} Devshiplog</p>
        <nav aria-label="약관" className="flex items-center gap-4">
          <Link
            href="/about"
            className="inline-flex min-h-touch items-center transition-colors hover:text-ink"
          >
            소개
          </Link>
          <Link
            href="/terms"
            className="inline-flex min-h-touch items-center transition-colors hover:text-ink"
          >
            이용약관
          </Link>
          <Link
            href="/privacy"
            className="inline-flex min-h-touch items-center transition-colors hover:text-ink"
          >
            개인정보처리방침
          </Link>
        </nav>
      </div>
    </footer>
  )
}
