import argparse
import getpass
import re
from sqlalchemy import select, delete
from .config import Settings
from .db import make_database, User, Subject, Membership, LoginSession
from .security import hash_password


def main():
    parser = argparse.ArgumentParser(description="DersAtlas yerel yönetim komutları")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user")
    create.add_argument("username")
    create.add_argument("--role", choices=["admin", "student"], default="admin")
    password = commands.add_parser("reset-password")
    password.add_argument("username")
    grant = commands.add_parser("grant")
    grant.add_argument("username")
    grant.add_argument("subject_id")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("username")
    revoke.add_argument("subject_id")
    commands.add_parser("list-subjects")
    args = parser.parse_args()
    settings = Settings()
    engine, factory = make_database(settings)
    with factory() as db:
        if args.command == "list-subjects":
            for subject in db.scalars(select(Subject)):
                print(subject.id, subject.name)
            return
        if not re.fullmatch(r"[a-zA-Z0-9_.-]{3,60}", args.username):
            raise SystemExit("Kullanıcı adı 3-60 Latin harf, sayı, nokta, tire veya alt çizgi olmalı.")
        user = db.scalar(select(User).where(User.username == args.username.lower()))
        if args.command in {"create-user", "reset-password"}:
            if args.command == "create-user" and user:
                raise SystemExit("Kullanıcı zaten var; reset-password kullan.")
            if args.command == "reset-password" and not user:
                raise SystemExit("Kullanıcı bulunamadı.")
            first = getpass.getpass("Parola (en az 12 karakter): ")
            if first != getpass.getpass("Parola tekrar: "):
                raise SystemExit("Parolalar eşleşmiyor.")
            hashed = hash_password(first)
            if user:
                user.password_hash = hashed
                db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
            else:
                user = User(username=args.username.lower(), password_hash=hashed, role=args.role)
                db.add(user)
                db.flush()
                if args.role == "admin":
                    db.add(Subject(owner_id=user.id, name="Tarih"))
            db.commit()
            print("Kullanıcı kaydedildi.")
        else:
            if not user or not db.get(Subject, args.subject_id):
                raise SystemExit("Kullanıcı veya ders bulunamadı.")
            existing = db.get(Membership, (args.subject_id, user.id))
            if args.command == "grant" and not existing:
                db.add(Membership(subject_id=args.subject_id, user_id=user.id))
            if args.command == "revoke" and existing:
                db.delete(existing)
            db.commit()
            print("Okuma izni güncellendi.")
    engine.dispose()


if __name__ == "__main__":
    main()
