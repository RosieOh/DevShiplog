"""글의 기술 스택과 검증 상태를 다룬다."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from src.application.errors import NotFoundError, ValidationError
from src.domain.enums import SignalKind
from src.domain.services import tech_stack
from src.domain.services.freshness import StackRef, evaluate
from src.infrastructure.database.models.post import Post
from src.infrastructure.database.models.tech import PostSignal, PostStack

MAX_STACKS = 12


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def suggest(content_md: str) -> List[Dict[str, Any]]:
    """본문에서 스택 후보를 뽑는다. 확정이 아니라 제안이다."""
    return [
        {
            "name": s.name,
            "version": s.version,
            "confidence": s.confidence,
            "evidence": s.evidence,
        }
        for s in tech_stack.detect(content_md)
    ]


def replace_stacks(db: Session, post_id: str, stacks: Sequence[Dict[str, Any]]) -> List[PostStack]:
    """글의 스택을 통째로 갈아끼운다.

    부분 갱신(추가/삭제)을 따로 두지 않는다. 발행 화면에서 목록을 통째로 편집하므로
    통째로 받는 편이 화면과 API 가 어긋날 여지가 없다.
    """
    if len(stacks) > MAX_STACKS:
        raise ValidationError(f"기술 스택은 최대 {MAX_STACKS}개까지 지정할 수 있습니다.")

    db.query(PostStack).filter(PostStack.post_id == post_id).delete(synchronize_session=False)

    saved: List[PostStack] = []
    seen = set()
    for position, item in enumerate(stacks):
        raw = str(item.get("name", "")).strip()
        # 모르는 이름은 버린다. 자유 문자열을 허용하면 "React"/"리액트"/"react.js" 가
        # 서로 다른 스택이 되고, 그러면 스택별 탐색이 성립하지 않는다.
        name = tech_stack.normalize(raw) or (raw.lower() if raw in tech_stack.ALIASES.values() else None)
        if not name or name in seen:
            continue
        seen.add(name)

        version = str(item.get("version") or "").strip() or None
        if version and not _looks_like_version(version):
            raise ValidationError(f"버전 형식이 올바르지 않습니다: {version}")

        row = PostStack(
            id=str(uuid.uuid4()),
            post_id=post_id,
            name=name,
            version=version,
            confidence=str(item.get("confidence") or "high"),
            position=position,
        )
        db.add(row)
        saved.append(row)

    db.commit()
    return saved


def _looks_like_version(value: str) -> bool:
    """18, 18.3, 3.12.1 은 받고 그 외는 거절한다."""
    parts = value.split(".")
    return len(parts) <= 3 and all(p.isdigit() for p in parts)


def mark_verified(db: Session, post_id: str, user_id: str) -> Dict[str, Any]:
    """작성자가 "지금도 동작한다" 고 확인한다.

    글 내용을 바꾸지 않아도 누를 수 있어야 한다. 확인은 편집과 다른 행위다 —
    "다시 돌려봤고 그대로 됐다" 는 것 자체가 독자에게 주는 정보다.
    """
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if not post:
        raise NotFoundError("글을 찾을 수 없습니다.")

    post.verified_at = _now()

    # 확인했으면 밀린 신호도 처리된 것으로 본다.
    # 안 그러면 갱신 목록에 영원히 남는다.
    db.query(PostSignal).filter(
        PostSignal.post_id == post_id, PostSignal.resolved_at.is_(None)
    ).update({PostSignal.resolved_at: post.verified_at}, synchronize_session=False)

    db.commit()
    return {"verified_at": post.verified_at.isoformat()}


def send_signal(
    db: Session, post_id: str, user_id: str, kind: str, note: Optional[str] = None
) -> Dict[str, Any]:
    """독자가 "따라 해봤다" 를 알린다.

    좋아요와 다르다. 좋아요는 "좋았다" 고 이건 "해봤다" 다.
    수는 훨씬 적지만 작성자에게는 훨씬 무거운 신호다.
    """
    try:
        signal_kind = SignalKind(kind)
    except ValueError as exc:
        raise ValidationError("알 수 없는 신호입니다.") from exc

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise NotFoundError("글을 찾을 수 없습니다.")
    if post.user_id == user_id:
        # 자기 글에 보내면 신호가 아니라 자기 확인이다. 그건 verify 로 한다.
        raise ValidationError("자기 글에는 검증 버튼을 사용해주세요.")

    existing = (
        db.query(PostSignal)
        .filter(PostSignal.post_id == post_id, PostSignal.user_id == user_id)
        .first()
    )
    if existing:
        # 마음이 바뀔 수 있다(다시 해보니 됐다). 새로 쌓지 않고 덮어쓴다.
        existing.kind = signal_kind
        existing.note = (note or "").strip()[:1000] or None
        existing.created_at = _now()
        existing.resolved_at = None
    else:
        db.add(
            PostSignal(
                id=str(uuid.uuid4()),
                post_id=post_id,
                user_id=user_id,
                kind=signal_kind,
                note=(note or "").strip()[:1000] or None,
            )
        )
    db.commit()
    return signal_summary(db, post_id, user_id)


def signal_summary(db: Session, post_id: str, viewer_id: Optional[str] = None) -> Dict[str, Any]:
    """현재 상태에 대한 신호만 센다.

    작성자가 고치고 다시 검증하면 그전 신호는 처리된 것으로 표시된다.
    처리된 신호까지 세면 "3명이 안 된다고 했습니다" 가 영원히 남아, 이미 고친 글을
    독자가 계속 의심하게 된다. 신호는 누적 평판이 아니라 지금 상태의 지표다.
    """
    rows = (
        db.query(PostSignal)
        .filter(PostSignal.post_id == post_id, PostSignal.resolved_at.is_(None))
        .all()
    )
    mine = next((r for r in rows if viewer_id and r.user_id == viewer_id), None)
    return {
        "works": sum(1 for r in rows if r.kind is SignalKind.WORKS),
        "broken": sum(1 for r in rows if r.kind is SignalKind.BROKEN),
        "my_signal": mine.kind.value if mine else None,
    }


def freshness_of(post: Post) -> Dict[str, Any]:
    """공개 페이지·목록에 실을 신선도."""
    refs = [StackRef(s.name, s.version) for s in (post.stacks or [])]
    result = evaluate(post.verified_at, post.published_at, refs)
    return {
        "level": result.level,
        "days_since_verified": result.days_since_verified,
        "outdated": result.outdated,
        "reason": result.reason,
        "verified_at": post.verified_at.isoformat() if post.verified_at else None,
    }


def stacks_of(post: Post) -> List[Dict[str, Any]]:
    return [{"name": s.name, "version": s.version} for s in (post.stacks or [])]
