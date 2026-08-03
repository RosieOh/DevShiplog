from typing import Any, Dict, Optional

from src.application.errors import NotFoundError, ValidationError
from src.domain.services.identity import InvalidHandleError, normalize_handle
from src.ports.output.repositories.user_repository import UserRepository

MAX_BIO = 300


class UpdateProfileUseCase:
    """블로그 신원 설정.

    handle 은 공개 URL(/@handle) 그 자체다. 한 번 바꾸면 기존 링크와 검색 색인이
    전부 깨지므로, 변경 자체는 허용하되 그 사실을 호출자에게 알려준다.
    """

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def execute(
        self,
        user_id: str,
        handle: Optional[str] = None,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")

        normalized: Optional[str] = None
        handle_changed = False

        if handle is not None:
            try:
                normalized = normalize_handle(handle)
            except InvalidHandleError as exc:
                raise ValidationError(str(exc)) from exc

            if normalized != user.handle:
                if self.user_repo.handle_taken(normalized, exclude_user_id=user_id):
                    raise ValidationError("이미 사용 중인 아이디입니다.")
                handle_changed = user.handle is not None

        if bio is not None and len(bio) > MAX_BIO:
            raise ValidationError(f"소개는 {MAX_BIO}자를 넘을 수 없습니다.")

        updated = self.user_repo.update_profile(
            user_id=user_id,
            handle=normalized,
            display_name=display_name,
            bio=bio,
            avatar_url=avatar_url,
        )

        return {
            "id": updated.id,
            "handle": updated.handle,
            "display_name": updated.display_name,
            "bio": updated.bio,
            "avatar_url": updated.avatar_url,
            # 기존 글의 주소가 통째로 바뀌었다는 신호. 화면에서 경고를 띄운다.
            "handle_changed": handle_changed,
        }


class CheckHandleUseCase:
    """가입/설정 화면에서 입력 즉시 사용 가능 여부를 알려준다."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def execute(self, handle: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            normalized = normalize_handle(handle)
        except InvalidHandleError as exc:
            return {"available": False, "handle": None, "reason": str(exc)}

        if self.user_repo.handle_taken(normalized, exclude_user_id=user_id):
            return {"available": False, "handle": normalized, "reason": "이미 사용 중인 아이디입니다."}

        return {"available": True, "handle": normalized, "reason": None}
