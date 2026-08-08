"""백업 스크립트.

왕복 복원은 CI 의 `backup` 잡이 실제 MariaDB 로 돌린다 (여기서는 못 한다 — SQLite 다).
여기서 지키는 건 그 앞단이다: **손상된 백업을 통과시키지 않는가**, 그리고
**보존 기간이 실제로 도는가**.

정작 필요한 날 "덤프가 비어 있었다" 를 알게 되는 게 가장 흔한 실패다.
"""

import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.backup import _prune
from scripts.restore import read_manifest
from scripts.verify_backup import _latest


def _make_backup(root: Path, name: str, *, created: datetime, corrupt: bool = False) -> Path:
    backup = root / name
    backup.mkdir(parents=True)
    dump = backup / "database.sql.gz"
    with gzip.open(dump, "wb") as handle:
        handle.write(b"-- dump\nINSERT INTO users VALUES (1);\n")

    digest = hashlib.sha256(dump.read_bytes()).hexdigest()
    if corrupt:
        # 기록된 체크섬은 그대로 두고 파일만 바꾼다 — 전송 중 잘린 상황과 같다.
        dump.write_bytes(dump.read_bytes()[: dump.stat().st_size // 2])

    (backup / "manifest.json").write_text(
        json.dumps(
            {
                "created_at": created.isoformat(),
                "app_version": "0.1.0",
                "database": "devshiplog",
                "alembic_revision": "0007_user_role",
                "dump_file": "database.sql.gz",
                "dump_bytes": dump.stat().st_size,
                "dump_sha256": digest,
                "row_counts": {"users": 1},
                "objects": {"files": 0},
            }
        ),
        encoding="utf-8",
    )
    return backup


def test_corrupt_dump_is_refused(tmp_path):
    """체크섬을 안 보면 잘린 파일을 복원하고 성공했다고 믿게 된다."""
    backup = _make_backup(tmp_path, "20260101T000000Z", created=datetime.now(timezone.utc), corrupt=True)
    with pytest.raises(SystemExit) as exc:
        read_manifest(backup)
    assert "손상" in str(exc.value)


def test_intact_dump_passes(tmp_path):
    backup = _make_backup(tmp_path, "20260101T000000Z", created=datetime.now(timezone.utc))
    assert read_manifest(backup)["row_counts"] == {"users": 1}


def test_missing_manifest_is_refused(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(SystemExit):
        read_manifest(tmp_path / "empty")


def test_missing_dump_is_refused(tmp_path):
    backup = _make_backup(tmp_path, "20260101T000000Z", created=datetime.now(timezone.utc))
    (backup / "database.sql.gz").unlink()
    with pytest.raises(SystemExit):
        read_manifest(backup)


def test_prune_drops_only_old_backups(tmp_path):
    """보존 기간이 없으면 디스크가 찰 때까지 쌓이고, 디스크가 차면 서비스가 멈춘다."""
    now = datetime.now(timezone.utc)
    _make_backup(tmp_path, "old", created=now - timedelta(days=30))
    _make_backup(tmp_path, "recent", created=now - timedelta(days=3))

    assert _prune(tmp_path, days=14) == 1
    assert not (tmp_path / "old").exists()
    assert (tmp_path / "recent").exists()


def test_prune_is_off_when_retention_is_zero(tmp_path):
    _make_backup(tmp_path, "ancient", created=datetime.now(timezone.utc) - timedelta(days=999))
    assert _prune(tmp_path, days=0) == 0
    assert (tmp_path / "ancient").exists()


def test_prune_ignores_unrelated_directories(tmp_path):
    """백업 디렉터리에 남의 폴더가 있어도 지우지 않는다."""
    (tmp_path / "not-a-backup").mkdir()
    _make_backup(tmp_path, "old", created=datetime.now(timezone.utc) - timedelta(days=30))
    assert _prune(tmp_path, days=14) == 1
    assert (tmp_path / "not-a-backup").exists()


def test_latest_picks_the_newest(tmp_path):
    now = datetime.now(timezone.utc)
    _make_backup(tmp_path, "20260101T000000Z", created=now)
    _make_backup(tmp_path, "20260301T000000Z", created=now)
    _make_backup(tmp_path, "20260201T000000Z", created=now)
    assert _latest(tmp_path).name == "20260301T000000Z"


def test_latest_fails_loudly_when_there_is_nothing(tmp_path):
    """백업이 없는데 조용히 넘어가면 '검증 통과' 로 보인다."""
    with pytest.raises(SystemExit):
        _latest(tmp_path)
