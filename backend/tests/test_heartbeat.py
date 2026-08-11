"""하트비트 (데드맨 스위치).

여기서 지키려는 것은 하나다:
**준비되지 않았는데 "살아 있다" 를 보내지 않는다.**

DB 가 끊긴 채로 신호를 보내면 감시자는 정상이라고 믿는다.
그건 하트비트가 없는 것보다 나쁘다 — 없으면 최소한 의심이라도 한다.
"""

import pytest

from src.infrastructure.observability import heartbeat


@pytest.fixture(autouse=True)
def _reset():
    heartbeat._state.update(
        {"configured": False, "last_success": None, "last_failure": None,
         "last_error": None, "sent": 0}
    )
    yield


@pytest.fixture()
def pinged(monkeypatch):
    """실제로 바깥에 요청하지 않는다. 어디로 보냈는지만 본다."""
    calls = []
    monkeypatch.setattr(heartbeat, "_ping", lambda url: calls.append(url) or True)
    return calls


def _set_url(monkeypatch, url="https://hc-ping.test/abc"):
    monkeypatch.setattr(heartbeat.settings, "HEARTBEAT_URL", url)


def _set_ready(monkeypatch, ready: bool):
    import src.infrastructure.observability.health as health

    monkeypatch.setattr(health, "readiness", lambda: {"ready": ready, "checks": []})


def test_does_nothing_without_a_url(pinged, monkeypatch):
    monkeypatch.setattr(heartbeat.settings, "HEARTBEAT_URL", "")
    assert heartbeat.beat_once() is False
    assert pinged == []


def test_sends_when_ready(pinged, monkeypatch):
    _set_url(monkeypatch)
    _set_ready(monkeypatch, True)

    assert heartbeat.beat_once() is True
    assert pinged == ["https://hc-ping.test/abc"]
    assert heartbeat.status()["sent"] == 1


def test_sends_failure_signal_when_not_ready(pinged, monkeypatch):
    """DB 가 끊긴 채로 "살아 있다" 를 보내면 감시자가 정상이라고 믿는다.

    실패 경로로 보내야 감시자가 타임아웃을 기다리지 않고 바로 알린다.
    """
    _set_url(monkeypatch)
    _set_ready(monkeypatch, False)

    heartbeat.beat_once()
    assert pinged == ["https://hc-ping.test/abc/fail"]

    state = heartbeat.status()
    assert state["sent"] == 0
    assert state["last_success"] is None
    assert state["last_failure"]


def test_readiness_failure_does_not_count_as_success(pinged, monkeypatch):
    """준비 상태 확인 자체가 터져도 성공으로 세면 안 된다."""
    _set_url(monkeypatch)
    import src.infrastructure.observability.health as health

    def broken():
        raise RuntimeError("DB 연결 실패")

    monkeypatch.setattr(health, "readiness", broken)

    heartbeat.beat_once()
    assert pinged == ["https://hc-ping.test/abc/fail"]
    assert heartbeat.status()["sent"] == 0


def test_network_failure_is_recorded_not_raised(monkeypatch):
    """하트비트가 실패했다고 서비스가 흔들리면 안 된다.

    _ping 을 가짜로 바꾸지 않는다 — 예외를 삼키는 것이 _ping 안에 있으므로,
    바꿔치면 정작 검증하려던 코드를 건너뛴다. 닫힌 포트로 실제로 붙어 본다.
    """
    _set_url(monkeypatch, "http://127.0.0.1:1/nope")
    _set_ready(monkeypatch, True)

    assert heartbeat.beat_once() is False
    state = heartbeat.status()
    assert state["last_failure"]
    assert state["sent"] == 0
    # 무엇 때문에 실패했는지 남아야 한다. 안 그러면 화면에 "실패" 만 뜬다.
    assert state["last_error"]


def test_trailing_slash_does_not_double_up(pinged, monkeypatch):
    _set_url(monkeypatch, "https://hc-ping.test/abc/")
    _set_ready(monkeypatch, True)
    heartbeat.beat_once()
    assert pinged == ["https://hc-ping.test/abc"]


def test_not_started_in_tests(monkeypatch):
    """테스트가 남의 감시 서비스를 두드리면 안 된다."""
    _set_url(monkeypatch)
    monkeypatch.setattr(heartbeat.settings, "ENVIRONMENT", "test")
    assert heartbeat.start([]) is None


def test_status_reports_whether_it_is_configured():
    """안 걸려 있으면 그 사실이 화면에 보여야 한다.

    "서버가 죽어도 아무도 모르는" 상태로 조용히 돌아가는 게 가장 나쁘다.
    """
    assert heartbeat.status()["configured"] is False
