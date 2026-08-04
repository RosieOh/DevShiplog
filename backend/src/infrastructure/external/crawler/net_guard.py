"""외부 URL 요청에 대한 SSRF 방어.

사용자가 임의의 URL 을 넣을 수 있으므로, 요청 전에 호스트를 실제로 resolve 해서
사설/루프백/링크로컬 대역으로 나가는 요청을 차단한다. 리다이렉트도 매 홉마다 검사한다.

한계: DNS rebinding (검사 시점과 연결 시점 사이에 A 레코드가 바뀌는 공격) 은
소켓 레벨에서 IP 를 고정해야 완전히 막을 수 있다. 프로덕션에서는 여기에 더해
egress 방화벽 또는 전용 프록시로 사설 대역을 차단하는 것을 권장한다.
"""

import ipaddress
import socket
from typing import List
from urllib.parse import urlparse

import httpx

from src.infrastructure.config.settings import settings

ALLOWED_SCHEMES = ("http", "https")
MAX_REDIRECTS = 5


class UnsafeURLError(ValueError):
    """차단된 URL (스킴 위반, 사설 대역 등)"""


def _resolve_ips(hostname: str) -> List[str]:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"호스트를 확인할 수 없습니다: {hostname}") from exc
    return list({info[4][0] for info in infos})


def _is_blocked_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_url(url: str) -> str:
    """URL 이 외부로 나가도 안전한지 검사한다. 안전하면 그대로 반환."""
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"허용되지 않는 스킴입니다: {parsed.scheme or '(없음)'}")
    if not parsed.hostname:
        raise UnsafeURLError("호스트가 없는 URL 입니다")

    if settings.CRAWLER_ALLOW_PRIVATE_NETWORK:
        return url

    for ip in _resolve_ips(parsed.hostname):
        if _is_blocked_ip(ip):
            raise UnsafeURLError(
                f"내부 네트워크 주소로는 요청할 수 없습니다: {parsed.hostname} -> {ip}"
            )
    return url


async def safe_get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """리다이렉트를 직접 따라가며 매 홉을 검증하는 GET.

    응답 본문은 settings.CRAWLER_MAX_BYTES 를 넘지 않도록 잘라서 읽는다.
    """
    current = validate_url(url)

    for _ in range(MAX_REDIRECTS + 1):
        request = client.build_request("GET", current, **kwargs)
        response = await client.send(request, follow_redirects=False, stream=True)

        if response.is_redirect:
            location = response.headers.get("location")
            await response.aclose()
            if not location:
                raise UnsafeURLError("Location 헤더가 없는 리다이렉트입니다")
            current = validate_url(str(httpx.URL(current).join(location)))
            continue

        try:
            body = bytearray()
            async for block in response.aiter_bytes():
                body.extend(block)
                if len(body) >= settings.CRAWLER_MAX_BYTES:
                    break
        finally:
            await response.aclose()

        # 잘라 읽은 본문으로 응답을 다시 구성한다.
        return httpx.Response(
            status_code=response.status_code,
            headers=response.headers,
            content=bytes(body),
            request=request,
        )

    raise UnsafeURLError("리다이렉트가 너무 많습니다")
