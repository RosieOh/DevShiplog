from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from ports.input.api.v1.dependencies import get_draft_repo
from ports.output.repositories.draft_repository import DraftRepository

router = APIRouter()


@router.get("/drafts/{draft_id}/export/md")
async def export_markdown(
    draft_id: str,
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Markdown 다운로드"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    latest_version = await draft_repo.get_latest_version(draft_id)
    if not latest_version:
        raise HTTPException(status_code=404, detail="No version found")
    
    content = latest_version.content_md or ""
    title = latest_version.meta_json.get("title", "draft") if latest_version.meta_json else "draft"
    filename = f"{title.replace(' ', '_')}.md"
    
    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

