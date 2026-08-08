"""백업 검증.

복원해 본 적 없는 백업은 백업이 아니라 희망이다.
정작 필요한 순간에 "덤프가 비어 있었다" 를 알게 되는 게 가장 흔한 실패다.

실제로 되살려 본다 — 임시 DB 를 만들어 복원하고, 표 별 행 수를 기록과 맞춘 뒤 지운다.
운영 DB 는 건드리지 않는다.

    python -m scripts.verify_backup ./backups/20260803T101500Z
    python -m scripts.verify_backup --latest
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.restore import (
    _dsn,
    compare_row_counts,
    create_database,
    drop_database,
    load_dump,
    read_manifest,
    with_admin,
)


def _latest(root: Path) -> Path:
    candidates = [p for p in root.iterdir() if (p / "manifest.json").exists()]
    if not candidates:
        raise SystemExit(f"백업이 없습니다: {root}")
    return sorted(candidates)[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="백업이 실제로 복원되는지 확인")
    parser.add_argument("backup", nargs="?", help="백업 디렉터리")
    parser.add_argument("--latest", action="store_true", help="가장 최근 백업을 검증")
    parser.add_argument("--root", default=os.getenv("BACKUP_DIR", "./backups"))
    parser.add_argument("--container", default="", help="mariadb 클라이언트가 없을 때 쓸 컨테이너")
    parser.add_argument("--admin-user", default="", help="임시 DB 를 만들 권한이 있는 계정")
    parser.add_argument("--admin-password", default="")
    args = parser.parse_args()

    if args.latest or not args.backup:
        backup = _latest(Path(args.root).resolve())
    else:
        backup = Path(args.backup).resolve()

    print(f"검증 대상: {backup}")
    # 체크섬 확인이 여기 들어 있다. 잘린 파일이면 여기서 멈춘다.
    manifest = read_manifest(backup)
    # 임시 DB 를 만들었다 지워야 하므로 관리 계정이 필요하다.
    dsn = with_admin(_dsn(), args.admin_user, args.admin_password)

    # 이름에 시각을 넣어 운영 DB 와 절대 겹치지 않게 한다.
    scratch = f"verify_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    if scratch == dsn["database"]:
        raise SystemExit("임시 DB 이름이 운영 DB 와 같습니다. 중단합니다.")

    print(f"임시 DB 에 복원: {scratch}")
    ok = False
    try:
        create_database(dsn, scratch)
        load_dump(dsn, scratch, backup / manifest["dump_file"], args.container or None)
        ok = compare_row_counts(dsn, scratch, manifest)
    finally:
        # 검증이 실패해도 임시 DB 는 반드시 치운다. 안 그러면 실패할 때마다 쌓인다.
        drop_database(dsn, scratch)
        print(f"임시 DB 정리: {scratch}")

    rows = sum(manifest["row_counts"].values())
    tables = len(manifest["row_counts"])
    if ok:
        print(f"검증 통과 — {tables}개 표 {rows:,}행이 그대로 되살아납니다.")
        return 0

    print("검증 실패 — 이 백업으로는 복원할 수 없습니다.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
