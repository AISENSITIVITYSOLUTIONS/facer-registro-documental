from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def get_by_id(self, db: Session, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return db.execute(stmt).scalar_one_or_none()
