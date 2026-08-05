"""초안 작성 템플릿 (인증 필요).

같은 형식의 글을 반복해서 쓸 때 매번 유형·독자·길이·문체를 다시 고르지 않도록
묶어 두는 것이다.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.application.errors import NotFoundError, ValidationError
from src.infrastructure.database.models.style_profile import StyleProfile
from src.infrastructure.database.models.template import Template
from src.infrastructure.database.session import get_db
from src.ports.input.api.v1.dependencies import get_current_user_id

router = APIRouter()

# 초안 생성 API 가 받는 값과 같아야 한다. 여기서만 자유 문자열을 허용하면
# 템플릿으로 만든 초안이 생성 단계에서 거절된다.
TYPES = {"implementation", "troubleshooting", "comparison", "retrospective", "tutorial"}
AUDIENCES = {"beginner", "intermediate", "advanced"}
LENGTHS = {"short", "default", "long"}

MAX_TEMPLATES_PER_USER = 50


class CreateTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str
    audience: str
    length_preset: str
    style_profile_id: Optional[str] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    type: str
    audience: str
    length_preset: str
    style_profile_id: Optional[str] = None
    created_at: str


def _payload(template: Template) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "type": template.type,
        "audience": template.audience,
        "length_preset": template.length_preset,
        "style_profile_id": template.style_profile_id,
        "created_at": template.created_at.isoformat() if template.created_at else "",
    }


def _owned(db: Session, template_id: str, user_id: str) -> Template:
    """소유 조건을 조회에 넣는다. 찾은 뒤에 비교하면 존재 여부가 새어나간다."""
    template = (
        db.query(Template)
        .filter(Template.id == template_id, Template.user_id == user_id)
        .first()
    )
    if not template:
        raise NotFoundError("템플릿을 찾을 수 없습니다.")
    return template


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    request: CreateTemplateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """템플릿을 만든다."""
    for value, allowed, label in (
        (request.type, TYPES, "유형"),
        (request.audience, AUDIENCES, "독자"),
        (request.length_preset, LENGTHS, "길이"),
    ):
        if value not in allowed:
            raise ValidationError(f"지원하지 않는 {label}입니다: {value}")

    if request.style_profile_id:
        # 남의 문체 프로필을 내 템플릿에 붙일 수 있으면 안 된다.
        owned_profile = (
            db.query(StyleProfile.id)
            .filter(
                StyleProfile.id == request.style_profile_id,
                StyleProfile.user_id == user_id,
            )
            .first()
        )
        if not owned_profile:
            raise NotFoundError("문체 프로필을 찾을 수 없습니다.")

    # 상한이 없으면 스크립트 하나로 테이블을 채울 수 있다.
    count = db.query(Template.id).filter(Template.user_id == user_id).count()
    if count >= MAX_TEMPLATES_PER_USER:
        raise ValidationError(f"템플릿은 최대 {MAX_TEMPLATES_PER_USER}개까지 만들 수 있습니다.")

    template = Template(
        user_id=user_id,
        name=request.name,
        type=request.type,
        audience=request.audience,
        length_preset=request.length_preset,
        style_profile_id=request.style_profile_id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _payload(template)


@router.get("", response_model=List[TemplateResponse])
def list_templates(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """내 템플릿 목록."""
    rows = (
        db.query(Template)
        .filter(Template.user_id == user_id)
        .order_by(Template.created_at.desc())
        .all()
    )
    return [_payload(t) for t in rows]


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _payload(_owned(db, template_id, user_id))


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    db.delete(_owned(db, template_id, user_id))
    db.commit()
    return {"deleted": True}
