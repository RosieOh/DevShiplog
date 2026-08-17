"""글이 아직 믿을 만한지 판단한다.

핵심 구분: **작성일과 검증일은 다르다.**

작성일은 "언제 썼는가" 다. 그건 글이 맞는지와 아무 상관이 없다.
2년 전에 쓴 글도 어제 다시 돌려봤다면 믿을 수 있고, 어제 쓴 글도 이미 틀렸을 수 있다.

그래서 우리가 세는 것은 **마지막으로 "지금도 된다" 고 확인한 시각**이다.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

# 검증 경과에 따른 단계.
#
# 6개월/18개월은 임의의 값이 아니라 프런트엔드 생태계의 주기에서 왔다.
# React·Next·Node 는 대략 6개월마다 마이너, 1~2년마다 메이저가 나온다.
# 6개월 안에 확인된 글은 대개 그대로 되고, 18개월이 넘으면 대개 뭔가 바뀌어 있다.
FRESH_DAYS = 180
AGING_DAYS = 540

FRESH = "fresh"
AGING = "aging"
STALE = "stale"
UNVERIFIED = "unverified"

# 우리가 아는 최신 메이저 버전.
#
# 레지스트리를 자동으로 긁지 않는다. 외부 의존성이 제품보다 커지고,
# 크롤링이 멈추면 판정이 조용히 틀려진다. 손으로 관리하되 출처를 남긴다.
# 갱신 시점: 2026-08. 반년마다 확인한다.
LATEST_MAJOR: Dict[str, int] = {
    "react": 19, "nextjs": 15, "vue": 3, "svelte": 5, "angular": 19,
    "nodejs": 22, "typescript": 5, "python": 3, "go": 1, "rust": 1,
    "java": 23, "kotlin": 2, "spring-boot": 3,
    "django": 5, "fastapi": 0, "flask": 3,
    "postgresql": 17, "mysql": 9, "mariadb": 11, "redis": 7, "mongodb": 8,
    "tailwindcss": 4, "vite": 6, "kubernetes": 1,
}

# 최신은 아니지만 **아직 멀쩡한** 메이저.
#
# 최신 메이저만 기준으로 삼으면 LTS 를 쓰는 글이 전부 뒤처진 것이 된다.
# Java 는 23 이 최신이지만 현업 대부분이 17·21(LTS)에 있고, Node 도 짝수 LTS 를 쓴다.
# 오늘 쓴 Spring Boot 3.2 + Java 17 글에 빨간 딱지를 붙이면
# 그 딱지는 곧 아무도 안 보는 딱지가 된다 — 경고는 흔해지는 순간 죽는다.
#
# LATEST_MAJOR 와 같은 이유로 손으로 관리한다. 지원 종료(EOL)가 지나면 여기서 뺀다.
# 갱신 시점: 2026-08.
STILL_SUPPORTED: Dict[str, set] = {
    # Java LTS. 8 은 뺐다 — 아직 쓰는 곳은 있지만 새 글의 기준으로는 낡았다.
    "java": {17, 21},
    # Node 짝수 버전만 LTS 가 된다.
    "nodejs": {20},
    # 유지보수 기간이 길어 실제로 많이 쓰인다.
    "postgresql": {15, 16},
    "python": {3},
}


@dataclass
class StackRef:
    name: str
    version: Optional[str] = None


@dataclass
class Freshness:
    level: str                    # fresh | aging | stale | unverified
    days_since_verified: Optional[int]
    # 메이저가 뒤처진 스택. 독자에게 "무엇이 바뀌었는지" 를 알려주기 위한 값이다.
    outdated: List[Dict[str, object]]
    reason: str                   # 화면에 그대로 쓸 수 있는 한 줄


def _major(version: Optional[str]) -> Optional[int]:
    if not version:
        return None
    try:
        return int(str(version).split(".")[0])
    except (ValueError, IndexError):
        return None


def outdated_stacks(stacks: List[StackRef]) -> List[Dict[str, object]]:
    """메이저 버전이 뒤처진 스택.

    마이너 차이는 세지 않는다. React 18.2 → 18.3 때문에 글이 틀리는 일은 드물고,
    그걸로 경고를 띄우면 경고가 흔해져서 아무도 안 본다.

    아직 지원되는 메이저(LTS 등)도 세지 않는다. 같은 이유다 —
    Java 17 글을 전부 뒤처진 것으로 치면 자바 글의 대부분이 빨갛게 된다.
    """
    behind = []
    for stack in stacks:
        current = LATEST_MAJOR.get(stack.name)
        written = _major(stack.version)
        if current is None or written is None:
            continue
        if written in STILL_SUPPORTED.get(stack.name, ()):
            continue
        if written < current:
            behind.append(
                {"name": stack.name, "version": stack.version, "latest_major": current}
            )
    return behind


def evaluate(
    verified_at: Optional[datetime],
    published_at: Optional[datetime],
    stacks: Optional[List[StackRef]] = None,
    now: Optional[datetime] = None,
) -> Freshness:
    """신선도를 매긴다.

    verified_at 이 없으면 published_at 을 쓰되 `unverified` 로 구분한다.
    "확인한 적 없음" 과 "확인했는데 오래됨" 은 독자에게 다른 정보다.
    """
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    stacks = stacks or []
    behind = outdated_stacks(stacks)

    baseline = verified_at or published_at
    if baseline is None:
        return Freshness(UNVERIFIED, None, behind, "검증 이력이 없습니다.")

    days = max(0, (now - baseline).days)

    if verified_at is None:
        # 한 번도 검증하지 않았다. 날짜만으로는 믿을 근거가 못 된다.
        level = STALE if days > AGING_DAYS else UNVERIFIED
        reason = f"작성 후 {days}일 동안 동작 확인이 없었습니다."
    elif days <= FRESH_DAYS:
        level, reason = FRESH, f"{days}일 전에 동작을 확인했습니다."
    elif days <= AGING_DAYS:
        level, reason = AGING, f"마지막 확인이 {days}일 전입니다."
    else:
        level, reason = STALE, f"마지막 확인이 {days}일 전입니다."

    # 메이저가 뒤처졌으면 검증이 아무리 최근이어도 **한 단계** 내린다.
    # "6개월 전에 확인함" 이 "React 17 기준" 을 덮지는 못한다.
    #
    # 한 단계씩만 내리는 게 중요하다. 예전에는 unverified 를 곧장 stale 로 보내서,
    # 오늘 쓴 글이 18개월 방치된 글과 같은 표시를 달았다. 독자가 날짜를 보고
    # "오늘 쓴 글인데 왜 오래됨이지" 라고 느끼는 순간 이 표시는 신뢰를 잃는다.
    if behind:
        names = ", ".join(f"{s['name']} {s['version']}" for s in behind[:3])
        if level == FRESH:
            level = AGING
        elif level == UNVERIFIED:
            # 검증한 적 없고 버전도 뒤처졌다 → "확인이 필요하다" 까지가 우리가 아는 전부다.
            level = AGING
        elif level == AGING:
            level = STALE
        reason = f"{names} 기준입니다. 이후 메이저 버전이 나왔습니다."

    return Freshness(level, days, behind, reason)
