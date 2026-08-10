"""백업.

DB 볼륨만 있고 백업이 없으면 실수 한 번에 전부 사라진다.
볼륨은 백업이 아니다 — 잘못된 DELETE 는 볼륨에도 그대로 반영된다.

두 가지를 받는다.
- 데이터베이스: 논리 덤프. 물리 복사본과 달리 버전이 달라도 되살릴 수 있다.
- 업로드된 파일: 오브젝트 저장소의 내용. 글 본문이 이 주소를 가리키므로
  DB 만 되살리면 모든 글의 이미지가 깨진 채로 돌아온다.

같이 남기는 manifest.json 이 핵심이다. 표 별 행 수를 적어 두지 않으면
복원한 결과가 맞는지 확인할 방법이 없고, 확인 못 하는 백업은 백업이 아니다.

    python -m scripts.backup
    python -m scripts.backup --out /mnt/backups --skip-objects
"""

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

from sqlalchemy import create_engine, inspect, text

from src.infrastructure.config.settings import settings


def _dsn() -> Dict[str, Any]:
    """SQLAlchemy URL 을 mariadb-dump 인자로 바꾼다."""
    parsed = urlparse(settings.DATABASE_URL)
    if not parsed.scheme.startswith("mysql"):
        raise SystemExit(
            f"이 스크립트는 MariaDB/MySQL 전용입니다 (현재: {parsed.scheme}). "
            "SQLite 로는 백업할 대상이 파일 하나뿐이라 그냥 복사하면 됩니다."
        )
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "/").lstrip("/"),
    }


def _dump_tool() -> str:
    """mariadb-dump 를 먼저 찾는다.

    MariaDB 11 부터 mysqldump 는 사라질 수 있는 별칭이다.
    도구가 없으면 컨테이너 안의 것을 쓴다 — 개발 기계에 클라이언트를 깔게 하고 싶지 않다.
    """
    for tool in ("mariadb-dump", "mysqldump"):
        if shutil.which(tool):
            return tool
    return ""


def _run_dump(dsn: Dict[str, Any], target: Path, container: Optional[str]) -> None:
    args = [
        f"--host={dsn['host']}",
        f"--port={dsn['port']}",
        f"--user={dsn['user']}",
        f"--password={dsn['password']}",
        # 잠그지 않고 일관된 스냅샷을 뜬다. 이게 없으면 백업 도중 서비스가 멈춘다.
        "--single-transaction",
        "--routines",
        "--triggers",
        "--default-character-set=utf8mb4",
        # 복원 대상이 비어 있지 않을 수 있다. 없으면 "이미 있다" 로 죽는다.
        "--add-drop-table",
        dsn["database"],
    ]

    tool = _dump_tool()
    if tool:
        command = [tool, *args]
    elif container:
        # 컨테이너 안에서는 host/port 를 아예 뺀다. 유닉스 소켓으로 붙는다 —
        # TCP 로 붙이면 바인딩 주소나 skip-networking 설정에 따라 붙지 못한다.
        inner = [a for a in args if not a.startswith(("--host=", "--port="))]
        command = ["docker", "exec", container, "mariadb-dump", *inner]
    else:
        raise SystemExit(
            "mariadb-dump 를 찾을 수 없습니다. 설치하거나 --container 로 "
            "DB 컨테이너 이름을 주세요 (예: --container devshiplog-db)."
        )

    # 덤프는 커질 수 있다. 통째로 메모리에 올리지 않고 바로 gzip 으로 흘려보낸다.
    with gzip.open(target, "wb") as out:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert process.stdout is not None
        for chunk in iter(lambda: process.stdout.read(1 << 20), b""):
            out.write(chunk)
        _, err = process.communicate()

    if process.returncode != 0:
        target.unlink(missing_ok=True)
        message = err.decode(errors="replace").strip()
        # 비밀번호가 인자에 있어서 오류 메시지에 그대로 실릴 수 있다.
        raise SystemExit(f"덤프 실패: {message.replace(dsn['password'], '***')}")


def _row_counts() -> Dict[str, int]:
    """표 별 행 수.

    복원한 뒤 이 수와 맞는지 보는 것이 유일한 자동 검증 수단이다.
    """
    engine = create_engine(settings.DATABASE_URL)
    counts: Dict[str, int] = {}
    try:
        with engine.connect() as conn:
            for table in inspect(engine).get_table_names():
                counts[table] = conn.execute(
                    text(f"SELECT COUNT(*) FROM `{table}`")
                ).scalar_one()
    finally:
        engine.dispose()
    return counts


def _backup_objects(target: Path) -> Dict[str, Any]:
    """오브젝트 저장소의 파일을 내려받는다."""
    if settings.STORAGE_BACKEND != "s3":
        source = Path(settings.UPLOAD_DIR)
        if not source.is_dir():
            return {"backend": "local", "files": 0, "bytes": 0}
        shutil.copytree(source, target, dirs_exist_ok=True)
        files = [p for p in target.rglob("*") if p.is_file()]
        return {
            "backend": "local",
            "files": len(files),
            "bytes": sum(p.stat().st_size for p in files),
        }

    from src.infrastructure.external.storage import get_storage

    storage = get_storage()
    client, bucket = storage.client, storage.bucket
    target.mkdir(parents=True, exist_ok=True)

    files = 0
    total = 0
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            key = item["Key"]
            destination = target / key
            destination.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, key, str(destination))
            files += 1
            total += item["Size"]
    return {"backend": "s3", "bucket": bucket, "files": files, "bytes": total}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _alembic_revision() -> Optional[str]:
    """스키마 버전.

    복원할 때 코드가 더 최신이면 마이그레이션을 더 돌려야 한다.
    이 값이 없으면 어디서부터 올려야 하는지 알 수 없다.
    """
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        return None
    finally:
        engine.dispose()


def _replicate(backup: Path, destination: str) -> Dict[str, Any]:
    """백업을 다른 곳으로 한 벌 더 옮긴다.

    같은 디스크에 둔 백업은 디스크가 죽는 순간 함께 죽는다.
    백업의 목적이 "이 기계가 사라져도 되살린다" 라면 사본은 다른 곳에 있어야 한다.

    목적지는 두 가지를 받는다.
    - 경로: 마운트된 다른 볼륨, NAS, rclone 이 감시하는 폴더
    - s3://버킷/접두어: 설정된 오브젝트 저장소 자격으로 올린다

    옮기고 나서 **다시 읽어 크기를 대조한다.** 복사가 조용히 잘리는 일은 실제로 있고,
    확인하지 않은 사본은 사본이 아니다.
    """
    files = [p for p in backup.rglob("*") if p.is_file()]

    if destination.startswith("s3://"):
        from src.infrastructure.external.storage import get_storage

        without_scheme = destination[len("s3://"):].strip("/")
        bucket, _, prefix = without_scheme.partition("/")
        client = get_storage().client
        copied = 0
        for path in files:
            key = "/".join(filter(None, [prefix, backup.name, path.relative_to(backup).as_posix()]))
            client.upload_file(str(path), bucket, key)
            # 올린 것을 다시 물어본다. 크기가 다르면 사본이 아니다.
            size = client.head_object(Bucket=bucket, Key=key)["ContentLength"]
            if size != path.stat().st_size:
                raise SystemExit(f"복제본 크기가 다릅니다: {key}")
            copied += 1
        return {"destination": destination, "files": copied, "verified": True}

    target = Path(destination).expanduser().resolve() / backup.name
    target.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in files:
        relative = path.relative_to(backup)
        (target / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target / relative)
        if (target / relative).stat().st_size != path.stat().st_size:
            raise SystemExit(f"복제본 크기가 다릅니다: {relative}")
        copied += 1
    return {"destination": str(target), "files": copied, "verified": True}


def _prune(root: Path, days: int) -> int:
    """오래된 백업을 지운다.

    보존 기간이 없으면 디스크가 찰 때까지 쌓이고, 디스크가 차면 서비스가 멈춘다.
    """
    if days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    removed = 0
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not (entry / "manifest.json").exists():
            continue
        created = json.loads((entry / "manifest.json").read_text(encoding="utf-8"))["created_at"]
        if datetime.fromisoformat(created) < cutoff:
            shutil.rmtree(entry)
            removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="DB + 업로드 파일 백업")
    parser.add_argument("--out", default=os.getenv("BACKUP_DIR", "./backups"))
    parser.add_argument(
        "--container",
        default=os.getenv("BACKUP_DB_CONTAINER", ""),
        help="로컬에 mariadb-dump 가 없을 때 쓸 DB 컨테이너 이름",
    )
    parser.add_argument("--skip-objects", action="store_true")
    parser.add_argument(
        "--replicate",
        default=os.getenv("BACKUP_REPLICATE_TO", ""),
        help="사본을 둘 곳. 경로 또는 s3://버킷/접두어. 같은 디스크의 백업은 디스크와 함께 죽는다.",
    )
    parser.add_argument(
        "--retention-days", type=int, default=int(os.getenv("BACKUP_RETENTION_DAYS", "14"))
    )
    args = parser.parse_args()

    dsn = _dsn()
    now = datetime.now(timezone.utc)
    root = Path(args.out).resolve()
    # 이름에 시각을 넣는다. 이름이 겹치면 방금 뜬 백업이 어제 것을 덮어쓴다.
    target = root / now.strftime("%Y%m%dT%H%M%SZ")
    target.mkdir(parents=True, exist_ok=False)

    print(f"백업 위치: {target}")

    dump_path = target / "database.sql.gz"
    print("데이터베이스 덤프 중...")
    _run_dump(dsn, dump_path, args.container or None)

    objects: Dict[str, Any] = {"skipped": True}
    if not args.skip_objects:
        print("업로드 파일 내려받는 중...")
        objects = _backup_objects(target / "objects")

    manifest = {
        "created_at": now.isoformat(),
        "app_version": settings.APP_VERSION,
        "database": dsn["database"],
        "alembic_revision": _alembic_revision(),
        "dump_file": dump_path.name,
        "dump_bytes": dump_path.stat().st_size,
        "dump_sha256": _sha256(dump_path),
        "row_counts": _row_counts(),
        "objects": objects,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    replication: Dict[str, Any] = {"configured": False}
    if args.replicate:
        print(f"사본 복제 중 → {args.replicate}")
        replication = {"configured": True, **_replicate(target, args.replicate)}
        manifest["replication"] = replication
        # manifest 를 다시 쓴다 — 복제 기록이 사본에는 없지만 원본에는 남아야
        # "이 백업은 어디로 갔는가" 를 나중에 알 수 있다.
        (target / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    pruned = _prune(root, args.retention_days)
    rows = sum(manifest["row_counts"].values())
    print(
        f"완료 — 덤프 {manifest['dump_bytes']:,}바이트 · "
        f"{len(manifest['row_counts'])}개 표 {rows:,}행 · "
        f"파일 {objects.get('files', 0)}개"
        + (f" · 오래된 백업 {pruned}건 정리" if pruned else "")
        + (f" · 사본 {replication['files']}개 → {replication['destination']}"
           if replication.get("configured") else "")
    )
    if not replication.get("configured"):
        # 조용히 넘어가면 "백업이 있다" 고 믿게 된다. 어디에 있는지가 중요하다.
        print("\n주의: 사본이 이 기계에만 있습니다. 디스크가 죽으면 백업도 함께 죽습니다.")
        print("      --replicate <경로|s3://버킷/접두어> 로 다른 곳에 한 벌 더 두세요.")
    print("\n이 백업은 아직 검증되지 않았습니다. 다음을 함께 돌리세요:")
    print(f"  python -m scripts.verify_backup {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
