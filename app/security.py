import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import HTTPException
from sqlalchemy import select, or_
from .db import Subject, Membership
from .passwords import hash_password, check_password, token_hash


def subject_filter(user):
    memberships = select(Membership.subject_id).where(Membership.user_id == user.id)
    return or_(Subject.owner_id == user.id, Subject.id.in_(memberships))


def require_subject(db, user, subject_id, write=False):
    subject = db.scalar(select(Subject).where(Subject.id == subject_id, subject_filter(user)))
    if not subject:
        raise HTTPException(404, "Ders bulunamadı veya erişim iznin yok.")
    if write and (subject.owner_id != user.id or user.role != "admin"):
        raise HTTPException(403, "Bu işlem dersin yöneticisine aittir.")
    return subject


class RateLimiter:
    """Tek süreç sınırı. Çoklu replika için paylaşımlı gateway gerekir."""
    def __init__(self):
        self.entries = defaultdict(deque)
        self.lock = Lock()

    def check(self, key, limit=10, window=60):
        now = time.monotonic()
        with self.lock:
            if len(self.entries) > 5000:
                self.entries = defaultdict(deque, {k: v for k, v in self.entries.items() if v and now - v[-1] < 3600})
            items = self.entries[key]
            while items and now - items[0] > window:
                items.popleft()
            if len(items) >= limit:
                raise HTTPException(429, "Çok sık istek gönderildi. Biraz sonra tekrar dene.")
            items.append(now)
