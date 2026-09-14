from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.agents import cancel_task
from api.auth import (
    existing_auth,
    issue_auth,
    password_hash,
    password_valid,
    require_user,
    user_view,
)
from api.db import get_db
from api.engine import player_view
from api.errors import GameError
from api.invoke_types import Credentials, Preferences
from api.models import DialogueRun, GameSession, ScriptVersion, User, UsageLedger, now
from api.providers import provider_status
from api.settings import settings

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
        return {"status": "ok", "database": "ready"}
    except Exception:
        return JSONResponse({"status": "unavailable"}, 503)


@router.get("/api/v1/me")
def me(request: Request, db: Session = Depends(get_db)):
    auth = existing_auth(request, db)
    return {
        "user": user_view(db.get(User, auth.user_id), auth)
        if auth and db.get(User, auth.user_id)
        else None
    }


@router.post("/api/v1/auth/guest")
def guest(request: Request, response: Response, db: Session = Depends(get_db)):
    auth = existing_auth(request, db)
    if auth:
        return {"user": user_view(db.get(User, auth.user_id), auth)}
    user = User(
        nickname="见习侦探",
        preferences={
            "provider": settings.provider,
            "theme": "dark",
            "font_size": "normal",
        },
    )
    db.add(user)
    db.commit()
    auth = issue_auth(db, response, user)
    return {"user": user_view(user, auth)}


@router.post("/api/v1/auth/register")
def register(
    body: Credentials,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    if db.scalar(select(User).where(User.username == body.username.lower())):
        raise GameError("USERNAME_TAKEN", "用户名已存在。", 409)
    auth = existing_auth(request, db)
    if auth:
        user = require_user(request, db)
        if user.username:
            raise GameError("ALREADY_REGISTERED", "当前档案已有账号，请先退出。", 409)
    else:
        default_provider = settings.provider if (
            settings.provider == "mock"
            or (settings.provider == "deepseek" and settings.deepseek_api_key)
            or (settings.provider == "openai" and settings.openai_api_key)
        ) else "mock"
        user = User(
            nickname=body.username,
            preferences={"provider": default_provider, "theme": "dark", "font_size": "normal"},
        )
        db.add(user)
        db.flush()
    user.username = body.username.lower()
    user.password = password_hash(body.password)
    db.commit()
    auth = issue_auth(db, response, user)
    return {"user": user_view(user, auth)}


@router.post("/api/v1/auth/login")
def login(
    body: Credentials,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.username == body.username.lower()))
    if (
        not user
        or not user.password
        or not password_valid(body.password, user.password)
    ):
        raise GameError("INVALID_CREDENTIALS", "用户名或密码不正确。", 401)
    old = existing_auth(request, db)
    if old:
        db.delete(old)
    auth = issue_auth(db, response, user)
    return {"user": user_view(user, auth)}


@router.post("/api/v1/auth/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    auth = existing_auth(request, db)
    if auth:
        db.delete(auth)
        db.commit()
    response.delete_cookie("casebook_session", path="/")
    return {"ok": True}


@router.patch("/api/v1/me/preferences")
def preferences(
    body: Preferences,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    if not next(p for p in provider_status() if p["id"] == body.provider)["configured"]:
        raise GameError(
            "MODEL_NOT_CONFIGURED", "请先在服务端环境变量中配置所选模型的密钥。", 409
        )
    user.nickname = body.nickname
    user.preferences = body.model_dump(exclude={"nickname"})
    db.commit()
    return {"user": user_view(user, existing_auth(request, db))}


@router.get("/api/v1/providers")
def providers(db: Session = Depends(get_db), user: User = Depends(require_user)):
    rows = db.scalars(
        select(UsageLedger).where(
            UsageLedger.owner_id == user.id, UsageLedger.created_at >= now()[:10]
        )
    ).all()
    return {
        "items": provider_status(),
        "daily_limit": settings.model_daily_call_limit,
        "calls_today": len(rows),
        "tokens_today": sum(r.tokens for r in rows),
        "delivery": "审核后语义块",
        "cost_status": "未配置单价，不估算金额",
    }


@router.get("/api/v1/privacy/export")
def export_data(db: Session = Depends(get_db), user: User = Depends(require_user)):
    games = db.scalars(select(GameSession).where(GameSession.owner_id == user.id)).all()
    own = db.scalars(
        select(ScriptVersion).where(ScriptVersion.owner_id == user.id)
    ).all()
    return {
        "format": "casebook-player-export-v1",
        "exported_at": now(),
        "profile": {"nickname": user.nickname, "username": user.username},
        "sessions": [player_view(db, g) for g in games],
        "my_scripts": [r.content for r in own],
    }


@router.delete("/api/v1/privacy/account")
async def delete_account(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    ids = list(
        db.scalars(select(GameSession.id).where(GameSession.owner_id == user.id))
    )
    runs = list(
        db.scalars(select(DialogueRun.id).where(DialogueRun.session_id.in_(ids)))
    )
    for rid in runs:
        cancel_task(rid)
    db.execute(delete(GameSession).where(GameSession.owner_id == user.id))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    response.delete_cookie("casebook_session", path="/")
    return {"ok": True}
