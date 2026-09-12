import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.errors import GameError
from api.models import AuthSession, User
from api.settings import settings


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=2**14, r=8, p=1
    ).hex()
    return f"{salt}:{digest}"


def password_valid(password: str, stored: str) -> bool:
    salt, digest = stored.split(":")
    value = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=2**14, r=8, p=1
    ).hex()
    return hmac.compare_digest(digest, value)


def issue_auth(db: Session, response: Response, user: User):
    raw = secrets.token_urlsafe(40)
    auth = AuthSession(
        token_hash=token_digest(raw),
        user_id=user.id,
        csrf=secrets.token_urlsafe(32),
        expires_at=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    )
    db.add(auth)
    db.commit()
    response.set_cookie(
        "casebook_session",
        raw,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=30 * 86400,
        path="/",
    )
    return auth


def existing_auth(request: Request, db: Session):
    raw = request.cookies.get("casebook_session", "")
    if not raw:
        return None
    auth = db.get(AuthSession, token_digest(raw))
    if auth and auth.expires_at > datetime.now(timezone.utc).isoformat():
        return auth
    return None


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = existing_auth(request, db)
    if not auth:
        raise GameError("UNAUTHENTICATED", "请刷新页面以恢复身份。", 401)
    if request.method not in ["GET", "HEAD", "OPTIONS"]:
        csrf = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(csrf, auth.csrf):
            raise GameError("CSRF_INVALID", "安全凭证已失效，请刷新后重试。", 403)
    user = db.scalar(select(User).where(User.id == auth.user_id))
    if not user:
        raise GameError("UNAUTHENTICATED", "当前身份已删除。", 401)
    return user


def user_view(user: User, auth: AuthSession):
    return {
        "id": user.id,
        "nickname": user.nickname,
        "username": user.username,
        "guest": user.username is None,
        "preferences": user.preferences,
        "csrf": auth.csrf,
    }
