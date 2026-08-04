import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from src.ports.input.api.v1.dependencies import get_current_user_id, get_draft_repo
from src.ports.input.api.v1.guards import get_owned_draft
from src.ports.output.repositories.draft_repository import DraftRepository

router = APIRouter()

_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n]+')


def _safe_filename(title: str) -> str:
    """파일명에 쓸 수 없는 문자를 제거하고 길이를 제한한다."""
    cleaned = _UNSAFE_FILENAME_CHARS.sub("", title or "").strip().replace(" ", "_")
    return (cleaned or "draft")[:80]


@router.get("/drafts/{draft_id}/md")
def export_markdown(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Markdown 다운로드"""
    get_owned_draft(draft_repo, draft_id, user_id)

    latest_version = draft_repo.get_latest_version(draft_id)
    if not latest_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="내보낼 버전이 없습니다."
        )

    meta = latest_version.meta_json or {}
    filename = f"{_safe_filename(meta.get('title', ''))}.md"

    return Response(
        content=latest_version.content_md or "",
        media_type="text/markdown; charset=utf-8",
        headers={
            # 한글 제목을 위해 RFC 5987 형식을 함께 제공한다.
            "Content-Disposition": (
                f"attachment; filename=\"draft.md\"; filename*=UTF-8''{quote(filename)}"
            )
        },
    )
