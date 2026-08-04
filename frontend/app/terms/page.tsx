import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: '이용약관 - Devshiplog',
  description: 'Devshiplog 서비스 이용약관',
}

export default function TermsPage() {
  return (
    <div className="bg-surface min-h-screen">
      <div className="max-w-4xl mx-auto px-[5%] py-16">
        <h1 className="text-4xl md:text-5xl font-bold text-ink mb-8 tracking-tight">이용약관</h1>
        <p className="text-ink-muted mb-12">최종 수정일: 2024년 1월 1일</p>

        <div className="space-y-12">
          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제1조 (목적)</h2>
            <p className="text-ink-muted leading-relaxed">
              본 약관은 Devshiplog(이하 &quot;회사&quot;)가 제공하는 기술 글 초안 생성 서비스(이하 &quot;서비스&quot;)의 이용과 관련하여 
              회사와 이용자 간의 권리, 의무 및 책임사항, 기타 필요한 사항을 규정함을 목적으로 합니다.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제2조 (정의)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. &quot;서비스&quot;란 회사가 제공하는 AI 기반 기술 글 초안 생성 플랫폼을 의미합니다.</p>
              <p>2. &quot;이용자&quot;란 본 약관에 따라 회사가 제공하는 서비스를 받는 회원 및 비회원을 의미합니다.</p>
              <p>3. &quot;회원&quot;이란 회사에 개인정보를 제공하여 회원등록을 한 자로서, 회사의 정보를 지속적으로 제공받으며, 
                 회사가 제공하는 서비스를 계속적으로 이용할 수 있는 자를 의미합니다.</p>
              <p>4. &quot;콘텐츠&quot;란 서비스를 통해 생성된 초안, 문서, 텍스트 등을 의미합니다.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제3조 (약관의 게시와 개정)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사는 본 약관의 내용을 이용자가 쉽게 알 수 있도록 서비스 초기 화면에 게시합니다.</p>
              <p>2. 회사는 필요한 경우 관련 법령을 위배하지 않는 범위에서 본 약관을 개정할 수 있습니다.</p>
              <p>3. 회사가 약관을 개정할 경우에는 적용일자 및 개정사유를 명시하여 현행약관과 함께 서비스 초기화면에 
                 그 적용일자 7일 이전부터 적용일자 전일까지 공지합니다.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제4조 (서비스의 제공 및 변경)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사는 다음과 같은 서비스를 제공합니다:</p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>URL, PR, 로그 파일을 통한 기술 글 초안 생성</li>
                <li>블로그 스타일 분석 및 적용 (Style DNA)</li>
                <li>민감정보 탐지 및 마스킹 (Safety 검사)</li>
                <li>마크다운 에디터 및 프리뷰 기능</li>
                <li>초안 버전 관리 및 내보내기</li>
              </ul>
              <p>2. 회사는 서비스의 내용을 변경할 수 있으며, 변경 시에는 사전에 공지합니다.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제5조 (서비스의 중단)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사는 컴퓨터 등 정보통신설비의 보수점검, 교체 및 고장, 통신의 두절 등의 사유가 발생한 경우에는 
                 서비스의 제공을 일시적으로 중단할 수 있습니다.</p>
              <p>2. 회사는 제1항의 사유로 서비스의 제공이 일시적으로 중단됨으로 인하여 이용자 또는 제3자가 입은 손해에 
                 대하여 배상합니다. 단, 회사가 고의 또는 과실이 없음을 입증하는 경우에는 그러하지 아니합니다.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제6조 (회원가입)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 이용자는 회사가 정한 가입 양식에 따라 회원정보를 기입한 후 본 약관에 동의한다는 의사표시를 함으로서 
                 회원가입을 신청합니다.</p>
              <p>2. 회사는 제1항과 같이 회원가입을 신청한 이용자 중 다음 각 호에 해당하지 않는 한 회원으로 등록합니다:</p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>가입신청자가 이전에 회원자격을 상실한 적이 있는 경우</li>
                <li>등록 내용에 허위, 기재누락, 오기가 있는 경우</li>
                <li>기타 회원으로 등록하는 것이 회사의 기술상 현저히 지장이 있다고 판단되는 경우</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제7조 (회원정보의 변경)</h2>
            <p className="text-ink-muted leading-relaxed">
              회원은 개인정보관리화면을 통하여 언제든지 본인의 개인정보를 열람하고 수정할 수 있습니다. 
              다만, 서비스 관리를 위해 필요한 실명, 아이디 등은 수정이 불가능합니다.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제8조 (개인정보보호)</h2>
            <p className="text-ink-muted leading-relaxed">
              회사는 이용자의 개인정보 수집 시 서비스제공을 위하여 필요한 범위에서 최소한의 개인정보를 수집합니다. 
              회사는 회원가입 시 구매계약이행에 필요한 정보를 미리 수집하지 않습니다. 
              또한, 이용자의 개인정보를 수집·이용하는 때에는 당해 이용자에게 그 목적을 고지하고 동의를 받습니다. 
              자세한 내용은 개인정보처리방침을 참고하시기 바랍니다.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제9조 (이용자의 의무)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 이용자는 다음 행위를 하여서는 안 됩니다:</p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>신청 또는 변경 시 허위내용의 등록</li>
                <li>타인의 정보 도용</li>
                <li>회사가 게시한 정보의 변경</li>
                <li>회사가 정한 정보 이외의 정보(컴퓨터 프로그램 등) 등의 송신 또는 게시</li>
                <li>회사와 기타 제3자의 저작권 등 지적재산권에 대한 침해</li>
                <li>회사 및 기타 제3자의 명예를 손상시키거나 업무를 방해하는 행위</li>
                <li>외설 또는 폭력적인 메시지, 화상, 음성, 기타 공서양속에 반하는 정보를 공개 또는 게시하는 행위</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제10조 (콘텐츠의 저작권)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 이용자가 서비스를 통해 생성한 콘텐츠에 대한 저작권은 이용자에게 귀속됩니다.</p>
              <p>2. 회사는 서비스 제공을 위해 필요한 범위 내에서 이용자가 생성한 콘텐츠를 사용할 수 있습니다.</p>
              <p>3. 이용자는 서비스를 통해 생성한 콘텐츠에 대해 제3자의 권리를 침해하지 않을 책임이 있습니다.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제11조 (면책조항)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사는 천재지변 또는 이에 준하는 불가항력으로 인하여 서비스를 제공할 수 없는 경우에는 
                 서비스 제공에 관한 책임이 면제됩니다.</p>
              <p>2. 회사는 회원의 귀책사유로 인한 서비스 이용의 장애에 대하여는 책임을 지지 않습니다.</p>
              <p>3. 회사는 회원이 서비스를 이용하여 기대하는 수익을 상실한 것에 대하여 책임을 지지 않으며, 
                 그 밖의 서비스를 통하여 얻은 자료로 인한 손해에 관하여 책임을 지지 않습니다.</p>
              <p>4. 회사가 제공하는 서비스의 품질이나 정확성에 대한 보장은 하지 않습니다.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제12조 (분쟁의 해결)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사와 이용자 간에 발생한 전자상거래 분쟁에 관한 소송은 제소 당시의 이용자의 주소에 의하고, 
                 주소가 없는 경우에는 거소를 관할하는 지방법원의 전속관할로 합니다.</p>
              <p>2. 회사와 이용자 간에 제기된 전자상거래 소송에는 한국법을 적용합니다.</p>
            </div>
          </section>
        </div>

        <div className="mt-16 pt-8 border-t border-line">
          <p className="text-ink-muted text-sm">
            본 약관에 대한 문의사항이 있으시면 다음 연락처로 문의해 주시기 바랍니다.
          </p>
          <p className="text-ink font-semibold mt-2">이메일: support@devshiplog.com</p>
        </div>
      </div>
    </div>
  )
}

