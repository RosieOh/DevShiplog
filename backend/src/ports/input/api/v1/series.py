"""시리즈 관리 (인증 필요). 공개 조회는 public.py 가 담당한다."""

from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.application.errors import NotFoundError
from src.domain.enums import PostStatus
from src.domain.services.identity import unique_slug
from src.infrastructure.external import revalidation
from src.ports.input.api.v1.dependencies import (
    get_current_user_id,
    get_post_repo,
    get_series_repo,
    get_user_repo,
)
from src.ports.output.repositories.post_repository import PostRepository
from src.ports.output.repositories.taxonomy_repository import SeriesRepository
from src.ports.output.repositories.user_repository import UserRepository

router = APIRouter()


class SeriesRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)


class SeriesPostRequest(BaseModel):
    post_id: str


class SeriesOrderRequest(BaseModel):
    # 원하는 순서대로 나열한 post id 목록
    post_ids: List[str] = Field(max_length=200)


def _owned(series_repo: SeriesRepository, series_id: str, user_id: str):
    series = series_repo.get_by_id(series_id)
    # 남의 시리즈에는 404 를 낸다. 403 을 내면 "그런 시리즈가 있긴 하다" 가 새어나간다.
    if not series or series.user_id != user_id:
        raise NotFoundError("시리즈를 찾을 수 없습니다.")
    return series


def _payload(series) -> Dict[str, Any]:
    return {
        "id": series.id,
        "slug": series.slug,
        "name": series.name,
        "description": series.description or "",
        "post_count": len(series.posts),
    }


def _notify(background: BackgroundTasks, user_repo: UserRepository, user_id: str) -> None:
    """시리즈가 바뀌면 그 사람 블로그의 공개 페이지 캐시를 깬다."""
    user = user_repo.get_by_id(user_id)
    if user and user.handle:
        background.add_task(revalidation.notify, [f"blog:{user.handle}"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_series(
    payload: SeriesRequest,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    slug = unique_slug(payload.name, series_repo.slugs_for_user(user_id))
    series = series_repo.create(
        user_id=user_id, slug=slug, name=payload.name, description=payload.description
    )
    _notify(background, user_repo, user_id)
    return _payload(series)


@router.get("")
def my_series(
    user_id: str = Depends(get_current_user_id),
    series_repo: SeriesRepository = Depends(get_series_repo),
):
    return [_payload(s) for s in series_repo.list_by_user(user_id)]


@router.get("/{series_id}")
def series_detail(
    series_id: str,
    user_id: str = Depends(get_current_user_id),
    series_repo: SeriesRepository = Depends(get_series_repo),
):
    series = _owned(series_repo, series_id, user_id)
    return {
        **_payload(series),
        "posts": [
            {
                "id": link.post.id,
                "title": link.post.title,
                "slug": link.post.slug,
                "status": link.post.status.value,
                "position": link.position,
            }
            for link in series.posts
            if link.post
        ],
    }


@router.delete("/{series_id}")
def delete_series(
    series_id: str,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """시리즈만 지운다. 안에 있던 글은 남는다 — 묶음을 푸는 것이지 글을 버리는 게 아니다."""
    _owned(series_repo, series_id, user_id)
    series_repo.delete(series_id)
    _notify(background, user_repo, user_id)
    return {"deleted": True}


@router.post("/{series_id}/posts", status_code=status.HTTP_201_CREATED)
def add_post(
    series_id: str,
    payload: SeriesPostRequest,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    series_repo: SeriesRepository = Depends(get_series_repo),
    post_repo: PostRepository = Depends(get_post_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    _owned(series_repo, series_id, user_id)

    post = post_repo.get_by_id(payload.post_id)
    if not post or post.user_id != user_id:
        raise NotFoundError("글을 찾을 수 없습니다.")

    series_repo.add_post(series_id, payload.post_id)
    _notify(background, user_repo, user_id)
    return {"added": True}


@router.delete("/{series_id}/posts/{post_id}")
def remove_post(
    series_id: str,
    post_id: str,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    _owned(series_repo, series_id, user_id)
    series_repo.remove_post(series_id, post_id)
    _notify(background, user_repo, user_id)
    return {"removed": True}


@router.put("/{series_id}/order")
def reorder(
    series_id: str,
    payload: SeriesOrderRequest,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """순서를 통째로 다시 매긴다.

    연재는 쓴 순서와 읽는 순서가 다를 때가 많다 (개론을 나중에 쓰는 식).
    순서를 못 바꾸면 시리즈는 그냥 태그와 다를 게 없다.
    """
    series = _owned(series_repo, series_id, user_id)

    known = {link.post_id for link in series.posts}
    unknown = [pid for pid in payload.post_ids if pid not in known]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이 시리즈에 없는 글이 포함되어 있습니다.",
        )

    series_repo.reorder(series_id, payload.post_ids)
    _notify(background, user_repo, user_id)
    return {"reordered": len(payload.post_ids)}
