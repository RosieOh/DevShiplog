from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from ports.input.api.v1.dependencies import get_db
from ports.input.api.v1.auth import get_current_user_id
from infrastructure.database.models.template import Template

router = APIRouter()


class CreateTemplateRequest(BaseModel):
    name: str
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


@router.post("", response_model=TemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """템플릿 생성"""
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
    
    return {
        "id": template.id,
        "name": template.name,
        "type": template.type,
        "audience": template.audience,
        "length_preset": template.length_preset,
        "style_profile_id": template.style_profile_id,
        "created_at": template.created_at.isoformat() if template.created_at else "",
    }


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """템플릿 목록 조회"""
    templates = db.query(Template).filter(Template.user_id == user_id).order_by(Template.created_at.desc()).all()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "type": t.type,
            "audience": t.audience,
            "length_preset": t.length_preset,
            "style_profile_id": t.style_profile_id,
            "created_at": t.created_at.isoformat() if t.created_at else "",
        }
        for t in templates
    ]


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """템플릿 조회"""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {
        "id": template.id,
        "name": template.name,
        "type": template.type,
        "audience": template.audience,
        "length_preset": template.length_preset,
        "style_profile_id": template.style_profile_id,
        "created_at": template.created_at.isoformat() if template.created_at else "",
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """템플릿 삭제"""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    db.delete(template)
    db.commit()
    
    return {"message": "Template deleted successfully"}

