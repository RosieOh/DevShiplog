"""제품 지표.

`docs/PRODUCT_STRATEGY.md` 6절에 적은 세 질문에 답한다.
셋이 안 돌면 신선도는 우리만 좋아하는 기능이고, 그때는 접는다.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.infrastructure.database.models.product_event import ProductEvent

logger = logging.getLogger(__name__)

# 이 수 아래에서는 결론내지 않는다.
#
# 5건으로 "루프가 안 돈다" 고 접으면 그건 측정이 아니라 성급함이다.
# 20건은 통계적 근거라기보다, 사람이 "해봤다" 고 말할 수 있는 최소선이다.
MIN_SAMPLE = 20

# 이벤트 이름
STACK_SUGGESTED = "stack_suggested"   # 발행 시 자동 추출 결과
STACK_CONFIRMED = "stack_confirmed"   # 작성자가 최종 확정한 결과
POST_VERIFIED = "post_verified"       # "지금도 된다" 를 눌렀다
SIGNAL_SENT = "signal_sent"           # 독자가 "해봤다" 를 보냈다


def record(
    db: Session,
    name: str,
    user_id: Optional[str] = None,
    post_id: Optional[str] = None,
    **payload: Any,
) -> None:
    """이벤트를 남긴다.

    실패해도 본 작업을 절대 깨지 않는다. 계측 때문에 발행이 실패하면
    계측을 꺼버리게 되고, 그러면 계측이 없는 것과 같다.
    """
    try:
        db.add(
            ProductEvent(
                id=str(uuid.uuid4()),
                name=name,
                user_id=user_id,
                post_id=post_id,
                payload=payload or None,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("이벤트 기록 실패: %s", name, exc_info=False)


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


def _count(db: Session, name: str, since: datetime) -> int:
    return (
        db.query(func.count(ProductEvent.id))
        .filter(ProductEvent.name == name, ProductEvent.created_at >= since)
        .scalar()
        or 0
    )


def stack_correction_rate(db: Session, days: int = 90) -> Dict[str, Any]:
    """질문 1 — 자동 추출이 쓸 만한가.

    작성자가 제안을 고친 비율이다. 해석에 주의가 필요하다.

    - 0% 에 가까우면 두 가지 중 하나다. 추출이 완벽하거나, **아무도 안 본다.**
      후자면 메타데이터를 신뢰할 수 없다. 그래서 "빈 채로 발행" 도 같이 센다.
    - 100% 에 가까우면 추출이 쓸모없다는 뜻이다.

    건강한 값은 그 사이 어딘가다. 20~50% 를 기대한다.
    """
    since = _since(days)
    rows = (
        db.query(ProductEvent)
        .filter(ProductEvent.name == STACK_CONFIRMED, ProductEvent.created_at >= since)
        .all()
    )
    if not rows:
        return {"publishes": 0, "corrected": 0, "rate": None, "published_empty": 0}

    corrected = sum(1 for r in rows if (r.payload or {}).get("corrected"))
    empty = sum(1 for r in rows if (r.payload or {}).get("confirmed_count", 0) == 0)
    return {
        "publishes": len(rows),
        "corrected": corrected,
        "rate": round(corrected / len(rows), 3),
        # 스택 없이 발행한 글. 이게 높으면 나머지 지표가 다 무의미하다.
        "published_empty": empty,
    }


def reverification_rate(db: Session, days: int = 180) -> Dict[str, Any]:
    """질문 2 — 갱신 루프가 도는가.

    **두 번째 검증부터가 진짜다.** 첫 검증은 발행 직후의 의욕이고,
    두 번째는 "이 제품이 나를 다시 데려왔는가" 다.
    """
    since = _since(days)
    rows = (
        db.query(ProductEvent.post_id, func.count(ProductEvent.id))
        .filter(
            ProductEvent.name == POST_VERIFIED,
            ProductEvent.created_at >= since,
            ProductEvent.post_id.isnot(None),
        )
        .group_by(ProductEvent.post_id)
        .all()
    )
    if not rows:
        return {"verified_posts": 0, "reverified_posts": 0, "rate": None}

    reverified = sum(1 for _, count in rows if count >= 2)
    return {
        "verified_posts": len(rows),
        "reverified_posts": reverified,
        "rate": round(reverified / len(rows), 3),
    }


def signal_response(db: Session, days: int = 180) -> Dict[str, Any]:
    """질문 3 — 독자 신호가 작성자를 움직이는가.

    "안 됐어요" 를 받은 글 중 그 뒤에 검증된 비율, 그리고 걸린 시간.
    이게 안 돌면 신호는 작성자에게 잔소리일 뿐이다.
    """
    since = _since(days)
    broken = (
        db.query(ProductEvent.post_id, func.min(ProductEvent.created_at))
        .filter(
            ProductEvent.name == SIGNAL_SENT,
            ProductEvent.created_at >= since,
            ProductEvent.post_id.isnot(None),
        )
        .group_by(ProductEvent.post_id)
        .all()
    )
    # payload 로 broken 만 거르려면 행을 다시 봐야 한다. 건수가 적으므로 그대로 읽는다.
    broken_posts: Dict[str, datetime] = {}
    for post_id, _ in broken:
        first = (
            db.query(ProductEvent)
            .filter(
                ProductEvent.name == SIGNAL_SENT,
                ProductEvent.post_id == post_id,
                ProductEvent.created_at >= since,
            )
            .order_by(ProductEvent.created_at.asc())
            .first()
        )
        if first and (first.payload or {}).get("kind") == "broken":
            broken_posts[post_id] = first.created_at

    if not broken_posts:
        return {"signaled_posts": 0, "responded": 0, "rate": None, "median_hours": None}

    lead_times: List[float] = []
    for post_id, signaled_at in broken_posts.items():
        # 시각 비교를 SQL 에 맡기지 않는다.
        #
        # SQLite 는 DATETIME 을 문자열로 저장해서, 같은 시각이라도 저장값
        # '...:39' 과 바인딩값 '...:39.000000' 의 문자열 비교가 어긋난다.
        # 실제로 이것 때문에 반응률이 0 으로 나왔다.
        # 건수가 적으므로 파이썬에서 비교한다 — 방언에 관계없이 정확하다.
        verified_times = [
            row[0]
            for row in db.query(ProductEvent.created_at)
            .filter(ProductEvent.name == POST_VERIFIED, ProductEvent.post_id == post_id)
            .all()
        ]
        after = [t for t in verified_times if t and t >= signaled_at]
        if after:
            lead_times.append((min(after) - signaled_at).total_seconds() / 3600)

    lead_times.sort()
    median = lead_times[len(lead_times) // 2] if lead_times else None
    return {
        "signaled_posts": len(broken_posts),
        "responded": len(lead_times),
        "rate": round(len(lead_times) / len(broken_posts), 3),
        "median_hours": round(median, 1) if median is not None else None,
    }


def summary(db: Session) -> Dict[str, Any]:
    """세 질문을 한 화면에.

    판정까지 같이 낸다. 숫자만 보여주면 "나쁘지 않네" 로 넘어가게 된다.
    """
    correction = stack_correction_rate(db)
    reverification = reverification_rate(db)
    response = signal_response(db)

    verdicts = []
    if correction["publishes"] < MIN_SAMPLE:
        # "표본이 부족합니다" 만 띄우면 얼마나 남았는지 알 수 없고,
        # 그러면 이 화면을 다시 볼 이유가 없다. 진척을 보여준다.
        remaining = MIN_SAMPLE - correction["publishes"]
        verdicts.append(
            f"판단하기에 이릅니다. 발행 {correction['publishes']}/{MIN_SAMPLE}건 — "
            f"{remaining}건 더 필요합니다."
        )
    else:
        if correction["published_empty"] / correction["publishes"] > 0.5:
            verdicts.append(
                "절반 넘는 글이 스택 없이 발행됩니다. 이러면 신선도가 대부분 '미검증' 입니다."
            )
        if correction["rate"] is not None and correction["rate"] < 0.05:
            verdicts.append("보정이 거의 없습니다. 추출이 완벽하거나, 아무도 확인하지 않습니다.")
        if reverification["rate"] is not None and reverification["rate"] < 0.1:
            verdicts.append("재검증이 거의 없습니다. 갱신 루프가 돌지 않습니다.")
        if response["rate"] is not None and response["rate"] < 0.2:
            verdicts.append("신호를 받아도 작성자가 움직이지 않습니다.")

    return {
        "stack_correction": correction,
        "reverification": reverification,
        "signal_response": response,
        # 표본이 얼마나 모였는지. 화면이 진행 막대를 그리는 데 쓴다.
        "sample": {
            "publishes": correction["publishes"],
            "required": MIN_SAMPLE,
            "ready": correction["publishes"] >= MIN_SAMPLE,
        },
        "verdicts": verdicts or ["세 지표 모두 기준선을 넘습니다."],
    }
