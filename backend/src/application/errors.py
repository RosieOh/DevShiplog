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


class ExternalServiceError(ApplicationError):
    """크롤링/LLM 등 외부 의존성 실패"""

    status_code = 502
