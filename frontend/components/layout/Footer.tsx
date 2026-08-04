import Link from 'next/link'

export default function Footer() {
  // 하드코딩된 연도는 해가 바뀌면 바로 낡는다.
  const year = new Date().getFullYear()

  return (
    <footer className="py-16 px-[5%] border-t border-black/10 flex flex-col md:flex-row justify-between items-center text-sm text-ink-muted gap-4 bg-canvas">
      <p>© {year} Devshiplog</p>
      {/*
        GitHub / Twitter / Blog 는 href 없는 <span> 에 cursor-pointer 만 붙어 있었다.
        링크처럼 보이지만 클릭도 키보드 포커스도 되지 않아 오히려 신뢰를 깎는다.
        실제 주소가 생기면 <Link> 로 되살린다.
      */}
      <nav aria-label="약관" className="flex items-center gap-4">
        <Link href="/terms" className="inline-flex items-center min-h-touch hover:text-ink transition-colors">
          이용약관
        </Link>
        <span aria-hidden="true">·</span>
        <Link href="/privacy" className="inline-flex items-center min-h-touch hover:text-ink transition-colors">
          개인정보처리방침
        </Link>
      </nav>
    </footer>
  )
}
