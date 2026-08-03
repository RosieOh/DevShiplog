"""블로그 신원 설정 (인증 필요)."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.application.use_cases.profile.update_profile import (
    CheckHandleUseCase,
    UpdateProfileUseCase,
)
from src.ports.input.api.v1.dependencies import get_current_user_id, get_user_repo
from src.ports.output.repositories.user_repository import UserRepository

router = APIRouter()


class ProfileRequest(BaseModel):
    handle: Optional[str] = Field(default=None, max_length=40)
    display_name: Optional[str] = Field(default=None, max_length=60)
    bio: Optional[str] = Field(default=None, max_length=300)
    avatar_url: Optional[str] = Field(default=None, max_length=1000)


@router.get("/me")
def get_my_profile(
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = user_repo.get_by_id(user_id)
    return {
        "id": user.id,
        "email": user.email,
        "handle": user.handle,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "post_count": user.post_count,
        "follower_count": user.follower_count,
        "following_count": user.following_count,
        # handle 이 없으면 발행할 수 없다. 화면에서 온보딩을 띄우는 신호.
        "needs_handle": user.handle is None,
    }


@router.put("/me")
def update_my_profile(
    payload: ProfileRequest,
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
):
    return UpdateProfileUseCase(user_repo).execute(
        user_id=user_id,
        handle=payload.handle,
        display_name=payload.display_name,
        bio=payload.bio,
        avatar_url=payload.avatar_url,
    )


@router.get("/handle-available")
def check_handle(
    handle: str = Query(min_length=1, max_length=40),
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """입력 즉시 사용 가능 여부를 알려준다."""
    return CheckHandleUseCase(user_repo).execute(handle, user_id)
