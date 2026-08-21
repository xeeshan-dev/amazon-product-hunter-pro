"""User registration and bearer-token authentication services."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config.settings import get_settings
from web_app.backend.db.models import User


class AuthService:
    """Create users, verify credentials, and manage access tokens."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def register_user(
        self,
        db: Session,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> User:
        normalized_email = self._normalize_email(email)
        if db.query(User).filter(User.email == normalized_email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account already exists for this email address",
            )

        user = User(
            email=normalized_email,
            password_hash=self.hash_password(password),
            full_name=full_name.strip() if full_name else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate(self, db: Session, email: str, password: str) -> User:
        user = db.query(User).filter(User.email == self._normalize_email(email)).first()
        if not user or not self.verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is inactive",
            )
        return user

    def create_access_token(self, user: User) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.JWT_EXPIRATION_MINUTES
        )
        return jwt.encode(
            {"sub": str(user.id), "exp": expires_at},
            self.settings.JWT_SECRET_KEY,
            algorithm=self.settings.JWT_ALGORITHM,
        )

    def get_user_from_token(self, db: Session, token: str) -> User:
        try:
            payload = jwt.decode(
                token,
                self.settings.JWT_SECRET_KEY,
                algorithms=[self.settings.JWT_ALGORITHM],
            )
            subject = payload.get("sub")
            user_id = int(subject)
        except (JWTError, TypeError, ValueError):
            raise self._invalid_token()

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise self._invalid_token()
        return user

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), password_hash.encode("utf-8")
            )
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _invalid_token() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
