"""라우터에서 반복되는 소유권 검사."""

from fastapi import HTTPException, status

from src.ports.output.repositories.draft_repository import DraftRepository


def get_owned_draft(draft_repo: DraftRepository, draft_id: str, user_id: str):
    """Draft 를 조회하고 소유자가 아니면 거부한다.

    존재 여부를 노출하지 않도록 남의 글도 404 로 응답한다.
    """
    draft = draft_repo.get_by_id(draft_id)
    if not draft or draft.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft 를 찾을 수 없습니다.")
    return draft
