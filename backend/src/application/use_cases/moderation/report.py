"""신고 / 차단.

공개 댓글이 열리는 순간 스팸은 들어온다. 임계치를 넘으면 사람이 볼 때까지
자동으로 가려서, 운영자가 없는 시간대에 피해가 누적되지 않게 한다.
"""

import logging
from typing import Any, Dict

from src.application.errors import NotFoundError, ValidationError
from src.domain.enums import PostStatus, ReportReason, ReportStatus, ReportTargetType
from src.ports.output.repositories.moderation_repository import BlockRepository, ReportRepository
from src.ports.output.repositories.post_repository import PostRepository
from src.ports.output.repositories.social_repository import CommentRepository
from src.ports.output.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# 서로 다른 사용자에게서 이만큼 신고가 쌓이면 검토 전까지 자동으로 가린다.
AUTO_HIDE_THRESHOLD = 5


class ReportContentUseCase:
    def __init__(
        self,
        report_repo: ReportRepository,
        post_repo: PostRepository,
        comment_repo: CommentRepository,
        user_repo: UserRepository,
    ):
        self.report_repo = report_repo
        self.post_repo = post_repo
        self.comment_repo = comment_repo
        self.user_repo = user_repo

    def execute(
        self,
        reporter_id: str,
        target_type: str,
        target_id: str,
        reason: str,
        detail: str = "",
    ) -> Dict[str, Any]:
        try:
            ttype = ReportTargetType(target_type)
            treason = ReportReason(reason)
        except ValueError:
            raise ValidationError("신고 유형이 올바르지 않습니다.") from None

        owner_id = self._resolve_owner(ttype, target_id)
        if owner_id == reporter_id:
            raise ValidationError("자신의 콘텐츠는 신고할 수 없습니다.")

        report = self.report_repo.create(reporter_id, ttype, target_id, treason, detail)
        if report is None:
            # 이미 신고한 대상. 사용자에게는 성공처럼 보여준다(중복 신고 유도 방지).
            return {"reported": True, "already": True, "auto_hidden": False}

        auto_hidden = False
        open_count = self.report_repo.count_open_for_target(ttype, target_id)
        if open_count >= AUTO_HIDE_THRESHOLD:
            auto_hidden = self._auto_hide(ttype, target_id)

        # 운영자에게 알린다. 신고 화면을 만들어도 들여다볼 이유가 생기지 않으면
        # 결국 아무도 안 보고, 그러면 화면이 있으나 마나다.
        #
        # 알림 자체가 실패해도 신고는 이미 접수됐다. 신고자에게 오류를 보여주면
        # 다시 신고하게 되고, 그건 큐만 부풀린다.
        try:
            from src.infrastructure.observability import alerts

            alerts.new_report(
                reason=treason.value,
                target_type=ttype.value,
                pending=len(self.report_repo.list_open(limit=100, offset=0)),
            )
        except Exception:  # noqa: BLE001
            logger.warning("신고 알림 실패", exc_info=True)

        return {"reported": True, "already": False, "auto_hidden": auto_hidden}

    def _resolve_owner(self, ttype: ReportTargetType, target_id: str) -> str:
        if ttype is ReportTargetType.POST:
            post = self.post_repo.get_by_id(target_id)
            if not post:
                raise NotFoundError("글을 찾을 수 없습니다.")
            return post.user_id
        if ttype is ReportTargetType.COMMENT:
            comment = self.comment_repo.get_by_id(target_id)
            if not comment:
                raise NotFoundError("댓글을 찾을 수 없습니다.")
            return comment.user_id
        user = self.user_repo.get_by_id(target_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        return user.id

    def _auto_hide(self, ttype: ReportTargetType, target_id: str) -> bool:
        if ttype is ReportTargetType.POST:
            self.post_repo.set_status(target_id, PostStatus.HIDDEN)
            return True
        if ttype is ReportTargetType.COMMENT:
            self.comment_repo.soft_delete(target_id)
            return True
        # 사용자 정지는 사람이 판단한다. 자동 처리하지 않는다.
        return False


class ToggleBlockUseCase:
    def __init__(self, block_repo: BlockRepository, user_repo: UserRepository):
        self.block_repo = block_repo
        self.user_repo = user_repo

    def execute(self, user_id: str, handle: str) -> Dict[str, Any]:
        target = self.user_repo.get_by_handle(handle)
        if not target:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        if target.id == user_id:
            raise ValidationError("자기 자신은 차단할 수 없습니다.")

        if self.block_repo.is_blocked(user_id, target.id):
            self.block_repo.unblock(user_id, target.id)
            return {"blocked": False}

        self.block_repo.block(user_id, target.id)
        return {"blocked": True}
