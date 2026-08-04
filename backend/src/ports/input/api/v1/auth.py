from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from src.infrastructure.auth.jwt_handler import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from src.ports.input.api.v1.dependencies import get_current_user_id, get_user_repo
from src.ports.output.repositories.user_repository import UserRepository

router = APIRouter()

# 다른 모듈이 기존처럼 import 할 수 있도록 재노출한다.
__all__ = ["router", "get_current_user_id"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPayload(BaseModel):
    id: str
    email: str
    name: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPayload


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    user_repo: UserRepository = Depends(get_user_repo),
):
    """회원가입"""
    email = request.email.lower()
    if user_repo.get_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 가입된 이메일입니다."
        )

    user = user_repo.create(
        email=email,
        name=request.name,
        password_hash=get_password_hash(request.password),
    )

    return AuthResponse(
        access_token=create_access_token(data={"sub": user.id}),
        user=UserPayload(id=user.id, email=user.email, name=user.name),
    )


@router.post("/login", response_model=AuthResponse)
def login(
    request: LoginRequest,
    user_repo: UserRepository = Depends(get_user_repo),
):
    """로그인"""
    user = user_repo.get_by_email(request.email.lower())

    # 계정 존재 여부가 드러나지 않도록 실패 사유를 구분하지 않는다.
    if not user or not user.password_hash or not verify_password(
        request.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    return AuthResponse(
        access_token=create_access_token(data={"sub": user.id}),
        user=UserPayload(id=user.id, email=user.email, name=user.name),
    )


@router.get("/me", response_model=UserPayload)
def me(
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """현재 로그인한 사용자"""
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다."
        )
    return UserPayload(id=user.id, email=user.email, name=user.name)
