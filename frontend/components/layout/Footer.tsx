import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="py-16 px-[5%] border-t border-black/10 flex flex-col md:flex-row justify-between items-center text-sm text-[#666666] gap-4 bg-[#f9f9f7]">
      <div>© 2024 Devshiplog</div>
      <div className="flex gap-5">
        <span className="hover:text-[#111111] cursor-pointer transition-colors">GitHub</span>
        <span className="hover:text-[#111111] cursor-pointer transition-colors">Twitter</span>
        <span className="hover:text-[#111111] cursor-pointer transition-colors">Blog</span>
      </div>
      <div className="flex gap-4">
        <Link href="/terms" className="hover:text-[#111111] transition-colors">
          이용약관
        </Link>
        <span>•</span>
        <Link href="/privacy" className="hover:text-[#111111] transition-colors">
          개인정보처리방침
        </Link>
      </div>
    </footer>
  )
}
