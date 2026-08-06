"""복원.

백업보다 이쪽이 중요하다. 복원해 본 적 없는 백업은 백업이 아니라 희망이다.

기본값이 안전한 쪽이다 — 대상 DB 이름을 반드시 적게 하고, 확인 문구 없이는 실행하지 않는다.
장애 한복판에서 손이 미끄러져 멀쩡한 DB 를 덮어쓰는 일이 실제로 일어난다.

    python -m scripts.restore ./backups/20260803T101500Z --into devshiplog_restored
    python -m scripts.restore ./backups/20260803T101500Z --into devshiplog --yes
"""

import argparse
import gzip
import os
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from src.infrastructure.config.settings import settings


def _dsn() -> Dict[str, Any]:
    parsed = urlparse(settings.DATABASE_URL)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "/").lstrip("/"),
    }


def with_admin(dsn: Dict[str, Any], user: str = "", password: str = "") -> Dict[str, Any]:
    """DB 를 만들고 지울 수 있는 계정으로 바꾼다.

    앱 계정에는 CREATE DATABASE 권한이 없다 — 있어서도 안 된다.
    복원과 검증은 자기 DB 를 새로 만들어야 하므로 그때만 관리 계정을 쓴다.
    """
    user = user or os.getenv("BACKUP_ADMIN_USER", "")
    password = password or os.getenv("BACKUP_ADMIN_PASSWORD", "")
    if not user:
        return dsn
    return {**dsn, "user": user, "password": password}


def _client_tool() -> str:
    for tool in ("mariadb", "mysql"):
        if shutil.which(tool):
            return tool
    return ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def admin_url(dsn: Dict[str, Any], database: str = "") -> str:
    """특정 DB 를 가리키는 접속 URL.

    복원 대상 DB 는 아직 없을 수 있으므로, 만들 때는 database 를 비워 접속한다.
    """
    from urllib.parse import quote

    auth = f"{quote(dsn['user'])}:{quote(dsn['password'])}"
    return f"mysql+pymysql://{auth}@{dsn['host']}:{dsn['port']}/{database}"


def create_database(dsn: Dict[str, Any], database: str) -> None:
    engine = create_engine(admin_url(dsn), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    except OperationalError as exc:
        if "Access denied" not in str(exc):
            raise
        # 여기서 그냥 스택트레이스를 뱉으면 "권한 문제" 라는 걸 알아채는 데 시간이 걸린다.
        # 장애 복구 중에 읽을 메시지다.
        raise SystemExit(
            f"'{dsn['user']}' 계정에는 DB 를 만들 권한이 없습니다.\n"
            "관리 계정을 지정하세요:\n"
            "  BACKUP_ADMIN_USER=root BACKUP_ADMIN_PASSWORD=... "
            "(또는 --admin-user/--admin-password)"
        ) from exc
    finally:
        engine.dispose()


def drop_database(dsn: Dict[str, Any], database: str) -> None:
    engine = create_engine(admin_url(dsn), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{database}`"))
    finally:
        engine.dispose()


def load_dump(
    dsn: Dict[str, Any], database: str, dump: Path, container: Optional[str] = None
) -> None:
    """gzip 덤프를 스트리밍으로 밀어 넣는다."""
    args = [
        f"--host={dsn['host']}",
        f"--port={dsn['port']}",
        f"--user={dsn['user']}",
        f"--password={dsn['password']}",
        "--default-character-set=utf8mb4",
        database,
    ]

    tool = _client_tool()
    if tool:
        command = [tool, *args]
    elif container:
        # 컨테이너 안에서는 유닉스 소켓으로 붙는다 (backup.py 와 같은 이유).
        inner = [a for a in args if not a.startswith(("--host=", "--port="))]
        command = ["docker", "exec", "-i", container, "mariadb", *inner]
    else:
        raise SystemExit(
            "mariadb 클라이언트를 찾을 수 없습니다. 설치하거나 --container 로 "
            "DB 컨테이너 이름을 주세요."
        )

    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdin is not None
    with gzip.open(dump, "rb") as handle:
        shutil.copyfileobj(handle, process.stdin, length=1 << 20)
    process.stdin.close()
    _, err = process.communicate()
    if process.returncode != 0:
        message = err.decode(errors="replace").strip()
        raise SystemExit(f"복원 실패: {message.replace(dsn['password'], '***')}")


def read_manifest(backup: Path) -> Dict[str, Any]:
    manifest_path = backup / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"manifest.json 이 없습니다: {backup}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    dump = backup / manifest["dump_file"]
    if not dump.exists():
        raise SystemExit(f"덤프 파일이 없습니다: {dump}")

    # 체크섬을 확인하지 않으면 조용히 잘린 파일을 복원하고 성공했다고 믿게 된다.
    actual = _sha256(dump)
    if actual != manifest["dump_sha256"]:
        raise SystemExit(
            "덤프가 손상되었습니다. 이 백업은 쓸 수 없습니다.\n"
            f"  기록: {manifest['dump_sha256']}\n  실제: {actual}"
        )
    return manifest


def restore_objects(backup: Path) -> int:
    """업로드 파일을 저장소로 되돌린다.

    DB 만 되살리면 글 본문의 이미지 주소가 전부 404 가 된다.
    """
    source = backup / "objects"
    if not source.is_dir():
        return 0

    if settings.STORAGE_BACKEND != "s3":
        destination = Path(settings.UPLOAD_DIR)
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, dirs_exist_ok=True)
        return sum(1 for p in source.rglob("*") if p.is_file())

    from src.infrastructure.external.storage import get_storage

    storage = get_storage()
    storage.ensure_bucket()
    uploaded = 0
    for path in source.rglob("*"):
        if path.is_file():
            key = path.relative_to(source).as_posix()
            storage.client.upload_file(str(path), storage.bucket, key)
            uploaded += 1
    return uploaded


def main() -> int:
    parser = argparse.ArgumentParser(description="백업에서 복원")
    parser.add_argument("backup", help="백업 디렉터리")
    parser.add_argument("--into", required=True, help="복원할 데이터베이스 이름")
    parser.add_argument("--container", default="", help="mariadb 클라이언트가 없을 때 쓸 컨테이너")
    parser.add_argument("--objects", action="store_true", help="업로드 파일도 되돌린다")
    parser.add_argument("--yes", action="store_true", help="확인 없이 진행")
    parser.add_argument("--admin-user", default="", help="DB 생성 권한이 있는 계정")
    parser.add_argument("--admin-password", default="")
    args = parser.parse_args()

    backup = Path(args.backup).resolve()
    manifest = read_manifest(backup)
    dsn = _dsn()

    print(f"백업 시각: {manifest['created_at']}")
    print(f"원본 DB : {manifest['database']} (스키마 {manifest['alembic_revision']})")
    print(f"대상 DB : {args.into} @ {dsn['host']}:{dsn['port']}")

    live = args.into == dsn["database"]
    if live and not args.yes:
        # 여기가 사고가 나는 지점이다. 장애 한복판에서 손이 미끄러진다.
        print(
            "\n지금 쓰고 있는 데이터베이스를 덮어쓰려 합니다. "
            "되돌릴 수 없습니다.\n--yes 를 붙여 다시 실행하세요.",
            file=sys.stderr,
        )
        return 1

    # DB 를 만드는 것만 관리 계정으로 한다. 데이터를 넣는 건 앱 계정이면 충분하다.
    admin = with_admin(dsn, args.admin_user, args.admin_password)
    create_database(admin, args.into)
    print("덤프 적용 중...")
    load_dump(admin, args.into, backup / manifest["dump_file"], args.container or None)

    restored = compare_row_counts(dsn, args.into, manifest)
    if args.objects:
        count = restore_objects(backup)
        print(f"업로드 파일 {count}개 복원")

    print("완료" if restored else "완료 (행 수가 기록과 다릅니다 — 위 내용을 확인하세요)")
    return 0 if restored else 1


def compare_row_counts(dsn: Dict[str, Any], database: str, manifest: Dict[str, Any]) -> bool:
    """복원 결과를 기록과 맞춰 본다.

    "복원 명령이 오류 없이 끝났다" 는 복원됐다는 뜻이 아니다.
    """
    engine = create_engine(admin_url(dsn, database))
    mismatches = []
    try:
        with engine.connect() as conn:
            for table, expected in manifest["row_counts"].items():
                actual = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one()
                if actual != expected:
                    mismatches.append((table, expected, actual))
    finally:
        engine.dispose()

    for table, expected, actual in mismatches:
        print(f"  불일치 {table}: 기록 {expected} · 복원 {actual}", file=sys.stderr)
    return not mismatches


if __name__ == "__main__":
    sys.exit(main())
