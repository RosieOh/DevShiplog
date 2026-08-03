"""SSRF 방어 검증. 사용자가 임의 URL 을 넣을 수 있으므로 회귀가 치명적이다."""

import pytest

from src.infrastructure.config.settings import settings
from src.infrastructure.external.crawler import net_guard
from src.infrastructure.external.crawler.net_guard import UnsafeURLError, validate_url


@pytest.fixture(autouse=True)
def block_private_network(monkeypatch):
    monkeypatch.setattr(settings, "CRAWLER_ALLOW_PRIVATE_NETWORK", False)


@pytest.fixture()
def resolves_to(monkeypatch):
    """DNS 결과를 고정한다 (테스트가 실제 네트워크에 의존하지 않도록)."""

    def _apply(ip: str):
        monkeypatch.setattr(net_guard, "_resolve_ips", lambda hostname: [ip])

    return _apply


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "gopher://example.com",
        "javascript:alert(1)",
    ],
)
def test_rejects_non_http_schemes(url):
    with pytest.raises(UnsafeURLError):
        validate_url(url)


def test_rejects_url_without_host():
    with pytest.raises(UnsafeURLError):
        validate_url("http://")


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",  # loopback
        "10.1.2.3",  # private A
        "172.16.0.9",  # private B
        "192.168.1.7",  # private C
        "169.254.169.254",  # 클라우드 메타데이터 (link-local)
        "0.0.0.0",  # unspecified
        "::1",  # IPv6 loopback
    ],
)
def test_rejects_internal_addresses(resolves_to, ip):
    resolves_to(ip)
    with pytest.raises(UnsafeURLError):
        validate_url("https://totally-innocent.example")


def test_allows_public_address(resolves_to):
    resolves_to("93.184.216.34")
    assert validate_url("https://example.com/post/1") == "https://example.com/post/1"


def test_dns_rebinding_style_hostname_is_blocked_by_resolution(resolves_to):
    """'localtest.me' 처럼 공개 도메인이 사설 IP 로 향하는 경우도 막힌다."""
    resolves_to("127.0.0.1")
    with pytest.raises(UnsafeURLError):
        validate_url("https://localtest.me")


def test_can_be_disabled_for_local_development(monkeypatch, resolves_to):
    monkeypatch.setattr(settings, "CRAWLER_ALLOW_PRIVATE_NETWORK", True)
    # 허용 모드에서는 DNS 조회 자체를 건너뛴다.
    assert validate_url("http://localhost:3000") == "http://localhost:3000"
