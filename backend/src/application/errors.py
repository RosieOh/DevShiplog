"""애플리케이션 계층 예외.

use case 는 HTTP 를 몰라야 하므로 여기 정의된 예외를 던지고,
ports/input/api 계층(main.py 의 exception handler)에서 상태 코드로 변환한다.
"""


class ApplicationError(Exception):
    """애플리케이션 계층 공통 예외"""

    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(ApplicationError):
    status_code = 404


class PermissionDeniedError(ApplicationError):
    status_code = 403


class ValidationError(ApplicationError):
    status_code = 422


class QuotaExceededError(ApplicationError):
    status_code = 429


class StaleDraftError(ApplicationError):
    """내가 읽은 뒤에 다른 곳에서 저장이 있었다.

    현재 내용을 함께 실어 보낸다. 클라이언트가 "덮어쓰기 / 상대 내용 보기" 를
    고를 수 있어야 하고, 그러려면 상대가 무엇을 썼는지 보여줄 수 있어야 한다.
    """

    status_code = 409

    def __init__(self, current_revision: int, content_md: str):
        super().__init__("다른 곳에서 이 글을 먼저 저장했습니다.")
        self.current_revision = current_revision
        self.content_md = content_md


class ExternalServiceError(ApplicationError):
    """크롤링/LLM 등 외부 의존성 실패"""

    status_code = 502
