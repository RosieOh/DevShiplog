"""운영자 권한을 준다/거둔다.

화면에서 올릴 수 없게 한 이유:
운영자를 만드는 버튼이 웹에 있으면 그 버튼 자체가 공격 표면이 된다.
운영자 승격은 서버에 들어갈 수 있는 사람만 할 수 있어야 한다.

    python -m scripts.grant_admin someone@example.com
    python -m scripts.grant_admin someone@example.com --revoke
    python -m scripts.grant_admin --list
"""

import argparse
import sys

from src.domain.enums import UserRole
from src.infrastructure.database.models.user import User
from src.infrastructure.database.session import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description="운영자 권한 관리")
    parser.add_argument("email", nargs="?", help="대상 사용자 이메일")
    parser.add_argument("--revoke", action="store_true", help="운영자 권한을 거둔다")
    parser.add_argument("--list", action="store_true", help="현재 운영자를 보여준다")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.list:
            admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
            if not admins:
                print("운영자가 없습니다.")
            for user in admins:
                print(f"{user.email}  (@{user.handle or '-'})")
            return 0

        if not args.email:
            parser.error("이메일을 지정하거나 --list 를 쓰세요.")

        user = db.query(User).filter(User.email == args.email).first()
        if not user:
            print(f"그런 사용자가 없습니다: {args.email}", file=sys.stderr)
            return 1

        if args.revoke:
            # 마지막 운영자를 거두면 신고를 볼 사람이 아무도 없게 된다.
            # 스스로 잠기는 실수는 막아 준다.
            remaining = (
                db.query(User)
                .filter(User.role == UserRole.ADMIN, User.id != user.id)
                .count()
            )
            if user.role is UserRole.ADMIN and remaining == 0:
                print("마지막 운영자입니다. 다른 운영자를 먼저 지정하세요.", file=sys.stderr)
                return 1
            user.role = UserRole.USER
            action = "일반 사용자로 내렸습니다"
        else:
            user.role = UserRole.ADMIN
            action = "운영자로 지정했습니다"

        db.commit()
        print(f"{user.email} 를 {action}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
