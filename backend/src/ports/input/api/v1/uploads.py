"""이미지 업로드 (인증 필요)."""

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from src.infrastructure.config.settings import settings
from src.infrastructure.external.storage.local_storage import (
    LocalStorageService,
    UnsupportedFileError,
)
from src.ports.input.api.v1.dependencies import (
    client_identity,
    enforce_rate_limit,
    get_current_user_id,
    get_user_repo,
)
from src.ports.output.repositories.user_repository import UserRepository

router = APIRouter()


class UploadResponse(BaseModel):
    url: str
    key: str
    size: int
    content_type: str


def _store(request: Request, user_id: str, file: UploadFile, prefix: str) -> UploadResponse:
    enforce_rate_limit("upload", client_identity(request, user_id))

    # 스트림을 통째로 읽기 전에 선언된 크기로 1차 차단한다.
    if file.size is not None and file.size > settings.MAX_UPLOAD_BYTES:
        limit_mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"파일이 너무 큽니다 (최대 {limit_mb}MB).",
        )

    data = file.file.read(settings.MAX_UPLOAD_BYTES + 1)
    try:
        stored = LocalStorageService().save(
            data=data,
            filename=file.filename or "upload",
            content_type=file.content_type or "",
            prefix=prefix,
        )
    except UnsupportedFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return UploadResponse(**stored.__dict__)


@router.post("/images", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_image(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """글 커버·본문 이미지 업로드."""
    return _store(request, user_id, file, prefix="posts")


@router.post("/avatar", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """프로필 사진 업로드. 업로드와 동시에 프로필에 반영한다."""
    result = _store(request, user_id, file, prefix="avatars")
    user_repo.update_profile(user_id=user_id, avatar_url=result.url)
    return result
