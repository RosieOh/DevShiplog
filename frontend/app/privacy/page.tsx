import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: '개인정보처리방침 - Devshiplog',
  description: 'Devshiplog 개인정보처리방침',
}

export default function PrivacyPage() {
  return (
    <div className="bg-surface min-h-screen">
      <div className="max-w-4xl mx-auto px-[5%] py-16">
        <h1 className="text-4xl md:text-5xl font-bold text-ink mb-8 tracking-tight">개인정보처리방침</h1>
        <p className="text-ink-muted mb-12">최종 수정일: 2024년 1월 1일</p>

        <div className="space-y-12">
          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제1조 (개인정보의 처리목적)</h2>
            <p className="text-ink-muted leading-relaxed mb-4">
              Devshiplog(이하 &quot;회사&quot;)는 다음의 목적을 위하여 개인정보를 처리합니다. 처리하고 있는 개인정보는 다음의 목적 이외의 용도로는 이용되지 않으며, 
              이용 목적이 변경되는 경우에는 개인정보 보호법 제18조에 따라 별도의 동의를 받는 등 필요한 조치를 이행할 예정입니다.
            </p>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p><strong className="text-ink">1. 회원 가입 및 관리</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>회원 가입의사 확인, 회원제 서비스 제공에 따른 본인 식별·인증, 회원자격 유지·관리</li>
                <li>서비스 부정이용 방지, 각종 고지·통지, 고충처리 목적</li>
              </ul>
              <p className="mt-4"><strong className="text-ink">2. 서비스 제공</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>기술 글 초안 생성 서비스 제공</li>
                <li>Style DNA 분석 및 적용</li>
                <li>Safety 검사 및 민감정보 탐지</li>
                <li>콘텐츠 버전 관리 및 저장</li>
              </ul>
              <p className="mt-4"><strong className="text-ink">3. 마케팅 및 광고 활용</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>신규 서비스 개발 및 맞춤 서비스 제공</li>
                <li>이벤트 및 광고성 정보 제공 및 참여기회 제공</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제2조 (개인정보의 처리 및 보유기간)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사는 법령에 따른 개인정보 보유·이용기간 또는 정보주체로부터 개인정보를 수집 시에 동의받은 개인정보 보유·이용기간 내에서 개인정보를 처리·보유합니다.</p>
              <p>2. 각각의 개인정보 처리 및 보유 기간은 다음과 같습니다:</p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li><strong className="text-ink">회원 가입 및 관리:</strong> 회원 탈퇴 시까지 (단, 관계 법령 위반에 따른 수사·조사 등이 진행중인 경우에는 해당 수사·조사 종료 시까지)</li>
                <li><strong className="text-ink">서비스 이용 기록:</strong> 3년 (통신비밀보호법)</li>
                <li><strong className="text-ink">계약 또는 청약철회 등에 관한 기록:</strong> 5년 (전자상거래법)</li>
                <li><strong className="text-ink">대금결제 및 재화 등의 공급에 관한 기록:</strong> 5년 (전자상거래법)</li>
                <li><strong className="text-ink">소비자의 불만 또는 분쟁처리에 관한 기록:</strong> 3년 (전자상거래법)</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제3조 (처리하는 개인정보의 항목)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>회사는 다음의 개인정보 항목을 처리하고 있습니다:</p>
              <p className="mt-4"><strong className="text-ink">1. 회원 가입 시 수집하는 정보</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>필수항목: 이메일, 비밀번호, 이름</li>
                <li>선택항목: 프로필 이미지, 블로그 URL</li>
              </ul>
              <p className="mt-4"><strong className="text-ink">2. 서비스 이용 과정에서 자동으로 생성되어 수집되는 정보</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>IP주소, 쿠키, MAC주소, 서비스 이용 기록, 방문 기록, 불량 이용 기록 등</li>
                <li>생성된 초안, 소스 URL, Style DNA 프로필 등</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제4조 (개인정보의 제3자 제공)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사는 정보주체의 개인정보를 제1조(개인정보의 처리목적)에서 명시한 범위 내에서만 처리하며, 
                 정보주체의 동의, 법률의 특별한 규정 등 개인정보 보호법 제17조 및 제18조에 해당하는 경우에만 개인정보를 제3자에게 제공합니다.</p>
              <p>2. 회사는 원칙적으로 정보주체의 개인정보를 제3자에게 제공하지 않습니다. 다만, 다음의 경우에는 예외로 합니다:</p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>정보주체가 사전에 동의한 경우</li>
                <li>법령의 규정에 의거하거나, 수사 목적으로 법령에 정해진 절차와 방법에 따라 수사기관의 요구가 있는 경우</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제5조 (개인정보처리의 위탁)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사는 원활한 개인정보 업무처리를 위하여 다음과 같이 개인정보 처리업무를 위탁하고 있습니다:</p>
              <div className="bg-bg p-6 rounded-[20px] mt-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 text-ink font-semibold">위탁업체</th>
                      <th className="text-left py-3 text-ink font-semibold">위탁업무 내용</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-border">
                      <td className="py-3">클라우드 서비스 제공업체</td>
                      <td className="py-3">서버 운영 및 데이터 저장</td>
                    </tr>
                    <tr className="border-b border-border">
                      <td className="py-3">결제 대행업체</td>
                      <td className="py-3">결제 처리 (유료 서비스 시)</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="mt-4">2. 회사는 위탁계약 체결 시 개인정보 보호법 제26조에 따라 위탁업무 수행목적 외 개인정보 처리금지, 
                 기술적·관리적 보호조치, 재위탁 제한, 수탁자에 대한 관리·감독, 손해배상 등에 관한 사항을 계약서 등 문서에 명시하고, 
                 수탁자가 개인정보를 안전하게 처리하는지를 감독하고 있습니다.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제6조 (정보주체의 권리·의무 및 그 행사방법)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 정보주체는 회사에 대해 언제든지 다음 각 호의 개인정보 보호 관련 권리를 행사할 수 있습니다:</p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>개인정보 처리정지 요구권</li>
                <li>개인정보 열람요구권</li>
                <li>개인정보 정정·삭제요구권</li>
                <li>개인정보 처리정지 요구권</li>
              </ul>
              <p className="mt-4">2. 제1항에 따른 권리 행사는 회사에 대해 서면, 전자우편, 모사전송(FAX) 등을 통하여 하실 수 있으며 
                 회사는 이에 대해 지체 없이 조치하겠습니다.</p>
              <p>3. 정보주체가 개인정보의 오류 등에 대한 정정 또는 삭제를 요구한 경우에는 회사는 정정 또는 삭제를 완료할 때까지 
                 당해 개인정보를 이용하거나 제공하지 않습니다.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제7조 (개인정보의 파기)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사는 개인정보 보유기간의 경과, 처리목적 달성 등 개인정보가 불필요하게 되었을 때에는 지체없이 해당 개인정보를 파기합니다.</p>
              <p>2. 개인정보 파기의 절차 및 방법은 다음과 같습니다:</p>
              <p className="mt-4"><strong className="text-ink">파기절차</strong></p>
              <p className="ml-4">회사는 파기 사유가 발생한 개인정보를 선정하고, 회사의 개인정보 보호책임자의 승인을 받아 개인정보를 파기합니다.</p>
              <p className="mt-4"><strong className="text-ink">파기방법</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-2">
                <li>전자적 파일 형태의 정보는 기록을 재생할 수 없는 기술적 방법을 사용합니다.</li>
                <li>종이에 출력된 개인정보는 분쇄기로 분쇄하거나 소각을 통하여 파기합니다.</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제8조 (개인정보 보호책임자)</h2>
            <div className="space-y-3 text-ink-muted leading-relaxed">
              <p>1. 회사는 개인정보 처리에 관한 업무를 총괄해서 책임지고, 개인정보 처리와 관련한 정보주체의 불만처리 및 피해구제 등을 위하여 
                 아래와 같이 개인정보 보호책임자를 지정하고 있습니다.</p>
              <div className="bg-bg p-6 rounded-[20px] mt-4">
                <p className="mb-2"><strong className="text-ink">개인정보 보호책임자</strong></p>
                <p>이메일: privacy@devshiplog.com</p>
                <p className="mt-4 mb-2"><strong className="text-ink">개인정보 보호 담당부서</strong></p>
                <p>이메일: support@devshiplog.com</p>
              </div>
              <p className="mt-4">2. 정보주체께서는 회사의 서비스를 이용하시면서 발생한 모든 개인정보 보호 관련 문의, 불만처리, 피해구제 등에 관한 사항을 
                 개인정보 보호책임자 및 담당부서로 문의하실 수 있습니다.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제9조 (개인정보의 안전성 확보조치)</h2>
            <p className="text-ink-muted leading-relaxed mb-4">회사는 개인정보의 안전성 확보를 위해 다음과 같은 조치를 취하고 있습니다:</p>
            <ul className="list-disc list-inside ml-4 space-y-2 text-ink-muted leading-relaxed">
              <li><strong className="text-ink">관리적 조치:</strong> 내부관리계획 수립·시행, 정기적 직원 교육 등</li>
              <li><strong className="text-ink">기술적 조치:</strong> 개인정보처리시스템 등의 접근권한 관리, 접근통제시스템 설치, 고유식별정보 등의 암호화, 보안프로그램 설치</li>
              <li><strong className="text-ink">물리적 조치:</strong> 전산실, 자료보관실 등의 접근통제</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink mb-4">제10조 (개인정보 처리방침 변경)</h2>
            <p className="text-ink-muted leading-relaxed">
              이 개인정보처리방침은 2024년 1월 1일부터 적용되며, 법령 및 방침에 따른 변경내용의 추가, 삭제 및 정정이 있는 경우에는 
              변경사항의 시행 7일 전부터 공지사항을 통하여 고지할 것입니다.
            </p>
          </section>
        </div>

        <div className="mt-16 pt-8 border-t border-border">
          <p className="text-ink-muted text-sm">
            본 개인정보처리방침에 대한 문의사항이 있으시면 다음 연락처로 문의해 주시기 바랍니다.
          </p>
          <p className="text-ink font-semibold mt-2">이메일: privacy@devshiplog.com</p>
        </div>
      </div>
    </div>
  )
}

