import Link from 'next/link'
import HeroRobot from '@/components/HeroRobot'

export default function Home() {
  return (
    <div className="bg-surface">
      {/* Hero Section */}
      <section className="h-screen flex flex-col justify-start pt-32 relative overflow-hidden">
        <HeroRobot />
        
        <div className="z-10 pointer-events-none relative max-w-[1400px] mx-auto px-[5%] w-full">
          <div className="max-w-2xl">
            <p className="uppercase tracking-widest text-xs mb-2.5 text-ink-muted">The helpful writing assistant</p>
            <h1 className="text-[clamp(40px,8vw,100px)] font-bold tracking-tight mb-5 text-ink text-left">
              기술 글 작성,
              <br />
              이제 쉽게
            </h1>
            <p className="text-lg text-ink-muted mb-10 text-left leading-relaxed">
              URL/PR/로그를 넣으면, 내 블로그 톤으로 기술 글 초안을 생성하고<br />
              안전/SEO 검수까지 마친 뒤 발행까지 이어주는 플랫폼
            </p>
            <div className="pointer-events-auto">
              <Link
                href="/drafts/new"
                className="bg-accent px-8 py-4 rounded-full text-sm font-semibold text-ink inline-block transition-opacity hover:opacity-85"
              >
                무료로 시작하기
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 bg-bg">
        <div className="max-w-[1400px] mx-auto px-[5%]">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-5xl font-bold text-ink mb-2">80%</div>
              <p className="text-ink-muted">작성 시간 단축</p>
            </div>
            <div className="text-center">
              <div className="text-5xl font-bold text-ink mb-2">60초</div>
              <p className="text-ink-muted">초안 생성 시간</p>
            </div>
            <div className="text-center">
              <div className="text-5xl font-bold text-ink mb-2">100%</div>
              <p className="text-ink-muted">안전 검사</p>
            </div>
            <div className="text-center">
              <div className="text-5xl font-bold text-ink mb-2">24/7</div>
              <p className="text-ink-muted">언제든지 사용</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section - Bento Grid */}
      <section className="py-24 px-[5%] max-w-[1400px] mx-auto">
        <div className="text-center mb-16">
          <p className="text-ink-muted mb-2.5">Designed for developers</p>
          <h2 className="text-5xl font-bold tracking-tight text-ink">기술 글 작성의 모든 것</h2>
        </div>

        <div className="grid grid-cols-12 gap-5">
          {/* Large Item */}
          <div className="col-span-12 md:col-span-8 bg-surface rounded-lg p-10 h-[500px] flex flex-col justify-between border border-border-subtle  transition-transform">
            <div>
              <h3 className="text-2xl font-bold mb-3 text-ink">AI 기반 초안 생성</h3>
              <p className="text-ink-muted text-base mb-4">
                URL, PR, 로그 파일을 입력하면 AI가 분석하여 완성도 높은 기술 글 초안을 자동으로 생성합니다.
              </p>
              <ul className="space-y-2 text-ink-muted text-sm">
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>GitHub PR/Issue URL 자동 분석 및 요약</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>에러 로그 및 디버깅 과정 자동 문서화</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>스트리밍 방식으로 실시간 생성 확인</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>목차, 제목 후보, 키포인트 자동 추출</span>
                </li>
              </ul>
            </div>
            <div className="w-full h-40 bg-surface-2 rounded mt-5 flex items-center justify-center">
              <div className="text-6xl">✨</div>
            </div>
          </div>

          {/* Small Item - Dark */}
          <div className="col-span-12 md:col-span-4 bg-ink rounded-lg p-10 h-[500px] flex flex-col justify-between text-bg  transition-transform">
            <div>
              <h3 className="text-2xl font-bold mb-3 text-bg">Style DNA</h3>
              <p className="text-bg/70 text-base mb-4">
                내 블로그 스타일을 학습하여 모든 글에서 일관된 톤과 문체를 유지합니다.
              </p>
              <ul className="space-y-2 text-bg/70 text-sm">
                <li className="flex items-start">
                  <span className="text-accent mr-2" aria-hidden="true">•</span>
                  <span>블로그 주소로 자동 스타일 분석</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent mr-2" aria-hidden="true">•</span>
                  <span>톤, 종결어미, 구조 선호도 추출</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent mr-2" aria-hidden="true">•</span>
                  <span>모든 초안에 자동 적용</span>
                </li>
              </ul>
            </div>
            <div className="w-full h-36 bg-bg/10 rounded-[20px] mt-5 flex items-center justify-center">
              <div className="text-4xl">🎨</div>
            </div>
          </div>

          {/* Medium Items */}
          <div className="col-span-12 md:col-span-6 bg-surface rounded-lg p-10 h-[400px] flex flex-col justify-between border border-border-subtle  transition-transform">
            <div>
              <h3 className="text-2xl font-bold mb-3 text-ink">Safety 검사</h3>
              <p className="text-ink-muted text-base mb-4">
                토큰, API 키, 회사 정보 등 민감정보를 자동으로 탐지하고 마스킹하여 안전하게 발행할 수 있습니다.
              </p>
              <ul className="space-y-2 text-ink-muted text-sm">
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>API 키, JWT, Bearer 토큰 자동 탐지</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>이메일, 전화번호, 내부 URL 마스킹</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>회사명 및 민감 정보 자동 필터링</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>발행 전 필수 체크 리스트 제공</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="col-span-12 md:col-span-6 bg-surface rounded-lg p-10 h-[400px] flex flex-col justify-between border border-border-subtle  transition-transform">
            <div>
              <h3 className="text-2xl font-bold mb-3 text-ink">원스톱 워크플로우</h3>
              <p className="text-ink-muted text-base mb-4">
                소스 추출부터 초안 생성, 검수, 발행까지 모든 과정을 한 곳에서 처리할 수 있습니다.
              </p>
              <ul className="space-y-2 text-ink-muted text-sm">
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>소스 추출 및 본문 자동 정리</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>마크다운 에디터 + 실시간 프리뷰</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>버전 관리 및 히스토리 추적</span>
                </li>
                <li className="flex items-start">
                  <span className="text-accent-text mr-2" aria-hidden="true">•</span>
                  <span>Copy & Download 즉시 지원</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Core Values Section */}
      <section className="py-24 bg-surface">
        <div className="max-w-[1400px] mx-auto px-[5%]">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold text-ink mb-4 tracking-tight">핵심 가치</h2>
            <p className="text-xl text-ink-muted">기술 글 작성 시간을 80% 단축</p>
          </div>

          <div className="grid md:grid-cols-3 gap-12">
            <div className="bg-bg p-10 rounded-lg border border-border-subtle">
              <div className="w-16 h-16 bg-accent rounded flex items-center justify-center mb-6">
                <svg className="w-8 h-8 text-ink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold mb-4 text-ink">입력 최소화</h3>
              <p className="text-ink-muted text-lg leading-relaxed">
                자료는 URL 한 줄만 넣으면 됩니다. 복잡한 입력 없이 바로 시작하세요.
              </p>
            </div>

            <div className="bg-bg p-10 rounded-lg border border-border-subtle">
              <div className="w-16 h-16 bg-accent rounded flex items-center justify-center mb-6">
                <svg className="w-8 h-8 text-ink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold mb-4 text-ink">내 문체 유지</h3>
              <p className="text-ink-muted text-lg leading-relaxed">
                블로그 주소로 Style DNA를 자동 생성하여 내 글쓰기 스타일을 그대로 유지합니다.
              </p>
            </div>

            <div className="bg-bg p-10 rounded-lg border border-border-subtle">
              <div className="w-16 h-16 bg-accent rounded flex items-center justify-center mb-6">
                <svg className="w-8 h-8 text-ink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold mb-4 text-ink">실무 안전장치</h3>
              <p className="text-ink-muted text-lg leading-relaxed">
                토큰/키/회사정보를 자동 탐지하고 마스킹하여 안전하게 발행할 수 있습니다.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-24 bg-bg">
        <div className="max-w-[1400px] mx-auto px-[5%]">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold text-ink mb-4 tracking-tight">작동 방식</h2>
            <p className="text-xl text-ink-muted">3단계로 간단하게</p>
          </div>

          <div className="max-w-5xl mx-auto">
            <div className="grid md:grid-cols-3 gap-8 mb-16">
              <div className="text-center">
                <div className="w-20 h-20 bg-ink text-bg rounded-full flex items-center justify-center text-3xl font-bold mx-auto mb-6">
                  01
                </div>
                <h4 className="text-xl font-bold mb-3 text-ink">소스 입력</h4>
                <p className="text-ink-muted leading-relaxed">
                  URL, PR 링크, 또는 텍스트/로그를 입력하세요.<br />
                  여러 소스를 동시에 입력할 수 있습니다.
                </p>
              </div>

              <div className="text-center">
                <div className="w-20 h-20 bg-ink text-bg rounded-full flex items-center justify-center text-3xl font-bold mx-auto mb-6">
                  02
                </div>
                <h4 className="text-xl font-bold mb-3 text-ink">초안 생성</h4>
                <p className="text-ink-muted leading-relaxed">
                  AI가 소스를 분석하여 기술 글 초안을 생성합니다.<br />
                  Style DNA를 적용하면 내 글쓰기 스타일로 자동 변환됩니다.
                </p>
              </div>

              <div className="text-center">
                <div className="w-20 h-20 bg-ink text-bg rounded-full flex items-center justify-center text-3xl font-bold mx-auto mb-6">
                  03
                </div>
                <h4 className="text-xl font-bold mb-3 text-ink">검수 및 발행</h4>
                <p className="text-ink-muted leading-relaxed">
                  Safety 검사로 민감정보를 확인하고,<br />
                  에디터에서 수정한 후 바로 발행하거나 복사할 수 있습니다.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Additional Features Grid */}
      <section className="py-24 px-[5%] max-w-[1400px] mx-auto bg-surface">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-ink mb-4 tracking-tight">추가 기능</h2>
          <p className="text-xl text-ink-muted">더 편리한 글 작성을 위한 도구들</p>
        </div>

        <div className="grid grid-cols-12 gap-5">
          <div className="col-span-12 md:col-span-4 bg-bg rounded-lg p-10 border border-border-subtle  transition-transform">
            <h3 className="text-2xl font-bold mb-3 text-ink">실시간 생성</h3>
            <p className="text-ink-muted text-base">
              스트리밍 방식으로 초안을 실시간으로 확인하며 생성 과정을 볼 수 있습니다.
            </p>
          </div>

          <div className="col-span-12 md:col-span-4 bg-bg rounded-lg p-10 border border-border-subtle  transition-transform">
            <h3 className="text-2xl font-bold mb-3 text-ink">버전 관리</h3>
            <p className="text-ink-muted text-base">
              생성된 초안의 모든 버전을 관리하고 이전 버전과 비교할 수 있습니다.
            </p>
          </div>

          <div className="col-span-12 md:col-span-4 bg-bg rounded-lg p-10 border border-border-subtle  transition-transform">
            <h3 className="text-2xl font-bold mb-3 text-ink">변형 기능</h3>
            <p className="text-ink-muted text-base">
              더 짧게, 더 길게, 쉽게, 더 딥하게 등 원하는 방향으로 초안을 변형할 수 있습니다.
            </p>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-24 bg-surface">
        <div className="max-w-[1400px] mx-auto px-[5%]">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold text-ink mb-4 tracking-tight">사용 사례</h2>
            <p className="text-xl text-ink-muted">이런 상황에서 유용합니다</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-bg p-10 rounded-lg border border-border-subtle">
              <h3 className="text-2xl font-bold mb-4 text-ink">PR 리뷰 후기 작성</h3>
              <p className="text-ink-muted text-lg leading-relaxed mb-4">
                GitHub PR을 URL로 입력하면, 코드 리뷰 과정과 배운 점을 정리한 기술 글 초안이 자동으로 생성됩니다.
              </p>
              <ul className="space-y-2 text-ink-muted">
                <li>• PR 링크만 입력하면 자동 분석</li>
                <li>• 코드 변경사항과 리뷰 내용 반영</li>
                <li>• 회고 형식으로 자동 구성</li>
              </ul>
            </div>

            <div className="bg-bg p-10 rounded-lg border border-border-subtle">
              <h3 className="text-2xl font-bold mb-4 text-ink">트러블슈팅 문서화</h3>
              <p className="text-ink-muted text-lg leading-relaxed mb-4">
                에러 로그나 디버깅 과정을 텍스트로 입력하면, 문제-원인-해결 과정을 정리한 글 초안이 생성됩니다.
              </p>
              <ul className="space-y-2 text-ink-muted">
                <li>• 로그 파일 직접 붙여넣기</li>
                <li>• 문제 해결 과정 자동 정리</li>
                <li>• 재현 가능한 가이드 생성</li>
              </ul>
            </div>

            <div className="bg-bg p-10 rounded-lg border border-border-subtle">
              <h3 className="text-2xl font-bold mb-4 text-ink">기술 스택 도입기</h3>
              <p className="text-ink-muted text-lg leading-relaxed mb-4">
                새로운 기술을 도입한 과정과 결과를 정리한 글을 빠르게 작성할 수 있습니다.
              </p>
              <ul className="space-y-2 text-ink-muted">
                <li>• 도입 배경부터 결과까지</li>
                <li>• 비교 분석 자동 생성</li>
                <li>• 팀 공유용 문서화</li>
              </ul>
            </div>

            <div className="bg-bg p-10 rounded-lg border border-border-subtle">
              <h3 className="text-2xl font-bold mb-4 text-ink">릴리즈 노트 작성</h3>
              <p className="text-ink-muted text-lg leading-relaxed mb-4">
                커밋 히스토리나 변경사항을 바탕으로 사용자 친화적인 릴리즈 노트를 생성합니다.
              </p>
              <ul className="space-y-2 text-ink-muted">
                <li>• 변경사항 자동 요약</li>
                <li>• 사용자 관점으로 재구성</li>
                <li>• 마크다운 형식으로 제공</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-24 bg-bg">
        <div className="max-w-[1400px] mx-auto px-[5%]">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold text-ink mb-4 tracking-tight">자주 묻는 질문</h2>
            <p className="text-xl text-ink-muted">궁금한 점을 확인하세요</p>
          </div>

          <div className="max-w-3xl mx-auto space-y-6">
            <div className="bg-surface p-8 rounded-lg border border-border-subtle">
              <h3 className="text-xl font-bold mb-3 text-ink">어떤 소스를 입력할 수 있나요?</h3>
              <p className="text-ink-muted leading-relaxed">
                GitHub PR/Issue URL, 블로그 글 URL, 텍스트, 로그 파일 등 다양한 형태의 소스를 입력할 수 있습니다. 
                여러 소스를 동시에 입력하여 종합적인 글을 생성할 수도 있습니다.
              </p>
            </div>

            <div className="bg-surface p-8 rounded-lg border border-border-subtle">
              <h3 className="text-xl font-bold mb-3 text-ink">Style DNA는 어떻게 작동하나요?</h3>
              <p className="text-ink-muted leading-relaxed">
                블로그 주소를 입력하면 최근 글들을 분석하여 톤, 종결어미, 구조 선호도 등을 추출합니다. 
                이후 생성되는 모든 초안에 이 스타일이 자동으로 적용됩니다.
              </p>
            </div>

            <div className="bg-surface p-8 rounded-lg border border-border-subtle">
              <h3 className="text-xl font-bold mb-3 text-ink">Safety 검사는 어떤 정보를 탐지하나요?</h3>
              <p className="text-ink-muted leading-relaxed">
                API 키, 토큰, 이메일, 전화번호, 내부 URL, 회사명 등 민감정보를 자동으로 탐지합니다. 
                발견된 정보는 마스킹하거나 삭제할 수 있으며, 무시할 수도 있습니다.
              </p>
            </div>

            <div className="bg-surface p-8 rounded-lg border border-border-subtle">
              <h3 className="text-xl font-bold mb-3 text-ink">생성된 초안을 수정할 수 있나요?</h3>
              <p className="text-ink-muted leading-relaxed">
                네, 마크다운 에디터에서 자유롭게 수정할 수 있습니다. 또한 &quot;더 짧게&quot;, &quot;더 길게&quot;, &quot;쉽게&quot;, 
                &quot;더 딥하게&quot; 등의 변형 기능을 사용하여 원하는 방향으로 조정할 수 있습니다.
              </p>
            </div>

            <div className="bg-surface p-8 rounded-lg border border-border-subtle">
              <h3 className="text-xl font-bold mb-3 text-ink">어떤 플랫폼에 발행할 수 있나요?</h3>
              <p className="text-ink-muted leading-relaxed">
                현재는 마크다운 파일로 다운로드하거나 클립보드에 복사할 수 있습니다. 
                향후 WordPress, Notion, Medium 등 다양한 플랫폼에 직접 발행하는 기능을 추가할 예정입니다.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-accent">
        <div className="max-w-[1400px] mx-auto px-[5%]">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-4xl md:text-5xl font-bold text-ink mb-6 tracking-tight">지금 바로 시작하세요</h2>
            <p className="text-xl md:text-2xl mb-12 text-ink leading-relaxed">
              기술 글 작성 시간을 80% 단축하고,<br />
              더 많은 글을 발행하세요
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/drafts/new"
                className="px-10 py-5 bg-ink text-bg rounded-full text-lg font-semibold transition-opacity hover:opacity-85"
              >
                무료로 시작하기
              </Link>
              <Link
                href="/onboarding/style"
                className="px-10 py-5 bg-surface text-ink border-2 border-ink rounded-full text-lg font-semibold hover:bg-bg transition-colors"
              >
                Style DNA 설정
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
