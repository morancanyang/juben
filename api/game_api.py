import asyncio
import json
import re
import time
from copy import deepcopy
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, desc, select, update
from sqlalchemy.orm import Session

from api.agents import cancel_task, run_event, start_task
from api.auth import require_user
from api.db import SessionLocal, get_db
from api.engine import (
    TERMINAL,
    check_active,
    commit_state,
    content_for,
    initial_state,
    note_view,
    owned_run,
    owned_session,
    player_view,
    public_script,
    receipt,
    save_receipt,
    score_submission,
    spend,
    take_action,
)
from api.errors import GameError
from api.invoke_types import (
    Action,
    DialogueRequest,
    NoteRequest,
    PartnerRequest,
    StartSession,
    Submission,
)
from api.models import (
    DialogueRun,
    GameSession,
    InvestigationEvent,
    Note,
    ScriptVersion,
    User,
    now,
)
from api.providers import partner_from_projection, provider_status
from api.scripts_api import visible_versions
from api.settings import settings

router = APIRouter(prefix="/api/v1")


@router.get("/sessions")
def session_list(db: Session = Depends(get_db), user: User = Depends(require_user)):
    rows = db.scalars(
        select(GameSession)
        .where(GameSession.owner_id == user.id)
        .order_by(desc(GameSession.updated_at))
        .limit(50)
    ).all()
    return {
        "items": [
            {
                "id": g.id,
                "script": public_script(db.get(ScriptVersion, g.script_version_id)),
                "phase": g.phase,
                "evidence_count": len(g.state["evidence"]),
                "score": g.state["result"]["score"] if g.state["result"] else None,
                "updated_at": g.updated_at,
                "version": g.version,
            }
            for g in rows
        ]
    }


@router.post("/sessions")
def create_session(
    body: StartSession,
    idem: str = Header("", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    old = receipt(db, user.id, "create-session", idem, body.model_dump())
    if old:
        return old
    row = next(
        (r for r in visible_versions(db, user) if r.script_id == body.script_id), None
    )
    if not row:
        raise GameError("NOT_FOUND", "找不到这本剧本。", 404)
    state = initial_state(body.model_dump(), row.content)
    game = GameSession(owner_id=user.id, script_version_id=row.id, state=state)
    db.add(game)
    db.flush()
    db.add(
        InvestigationEvent(
            session_id=game.id,
            seq=1,
            kind="started",
            payload={"script_version_id": row.id},
        )
    )
    result = {"session_id": game.id, "state": player_view(db, game)}
    save_receipt(db, user.id, "create-session", idem, body.model_dump(), result)
    db.commit()
    return result


@router.get("/sessions/{sid}/state")
def state(sid: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return player_view(db, owned_session(db, sid, user.id))


@router.get("/sessions/{sid}/evidence/{eid}")
def evidence_detail(
    sid: str,
    eid: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    view = player_view(db, owned_session(db, sid, user.id))
    item = next((e for e in view["evidence"] if e["id"] == eid), None)
    if not item:
        raise GameError("NOT_FOUND", "尚未发现这件证物。", 404)
    return item


@router.post("/sessions/{sid}/actions")
def action(
    sid: str,
    body: Action,
    idem: str = Header("", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    game = owned_session(db, sid, user.id)
    old = receipt(db, user.id, f"action:{sid}", idem, body.model_dump())
    if old:
        return old
    check_active(db, game, body.expected_version)
    new_state, message = take_action(
        content_for(db, game), game.state, body.model_dump()
    )
    commit_state(db, game, new_state, "action", {"type": body.type, "message": message})
    result = {"message": message, "state": player_view(db, game)}
    save_receipt(db, user.id, f"action:{sid}", idem, body.model_dump(), result)
    db.commit()
    return result


@router.post("/sessions/{sid}/dialogue-runs")
async def dialogue(
    sid: str,
    body: DialogueRequest,
    idem: str = Header("", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    game = owned_session(db, sid, user.id)
    old = receipt(db, user.id, f"dialogue:{sid}", idem, body.model_dump())
    if old:
        return old
    check_active(db, game, body.expected_version)
    case = content_for(db, game)
    actor = next((a for a in case["characters"] if a["id"] == body.actor_id), None)
    if not actor:
        raise GameError("NOT_FOUND", "找不到这位角色。", 404)
    provider = user.preferences.get("provider", settings.provider)
    # Accounts created before model integration were pinned to the mock
    # provider.  If a real provider is now configured, use it automatically;
    # the preferences endpoint can still explicitly switch an account back to
    # mock for offline testing.
    if provider == "mock" and settings.provider != "mock" and settings.deepseek_api_key:
        provider = settings.provider
    if not next(p for p in provider_status() if p["id"] == provider)["configured"]:
        raise GameError("MODEL_NOT_CONFIGURED", "该模型尚未配置密钥。", 409)
    new = deepcopy(game.state)
    spend(new)
    astate = new["characters"][actor["id"]]
    # Keep an episodic memory per NPC.  Older sessions may predate this field,
    # so hydrate it lazily without changing their existing question cache.
    amemory = astate.setdefault(
        "agent_memory",
        {
            "topics_discussed": [],
            "last_question": "",
            "contradictions": [],
            "promises": [],
            "trust_history": [astate.get("trust", 40)],
            "known_player_claims": [],
        },
    )
    repeated = body.question in astate["questions"]
    astate["alertness"] = min(100, astate["alertness"] + (12 if repeated else 3))
    astate["trust"] = max(0, min(100, astate["trust"] + (-2 if repeated else 2)))
    astate["emotion"] = "警觉" if astate["alertness"] >= 50 else astate["emotion"]
    topics = amemory.setdefault("topics_discussed", [])
    if body.question not in topics:
        topics.append(body.question)
    amemory["topics_discussed"] = topics[-24:]
    amemory["last_question"] = body.question
    history = amemory.setdefault("trust_history", [])
    history.append(astate["trust"])
    amemory["trust_history"] = history[-24:]
    if repeated:
        contradictions = amemory.setdefault("contradictions", [])
        marker = f"重复追问：{body.question}"
        if marker not in contradictions:
            contradictions.append(marker)
        amemory["contradictions"] = contradictions[-12:]
    # Preserve the player's wording as a claim the NPC has heard; this is
    # private to the selected NPC and is never sent to other agents.
    claims = amemory.setdefault("known_player_claims", [])
    claims.append(body.question)
    amemory["known_player_claims"] = claims[-24:]
    run = DialogueRun(
        id=str(uuid4()),
        session_id=sid,
        actor_id=actor["id"],
        question=body.question,
        base_version=game.version + 1,
        status="queued",
        provider=provider,
        events=[],
    )
    run_event(run, "run.status", status="queued")
    new["active_run"] = run.id
    new["messages"].append(
        {
            "id": run.id + ":user",
            "run_id": run.id,
            "actor_id": actor["id"],
            "actor_name": "你",
            "role": "user",
            "text": body.question,
            "time": now(),
        }
    )
    new["journal"].append(
        {
            "text": f"询问{actor['name']}。信任{astate['trust']}，警觉{astate['alertness']}；原因："
            + ("重复追问" if repeated else "正常询问"),
            "time": now(),
        }
    )
    db.add(run)
    commit_state(
        db,
        game,
        new,
        "dialogue_started",
        {"actor_id": actor["id"], "run_id": run.id, "repeated": repeated},
    )
    result = {"run_id": run.id, "status": "queued", "state": player_view(db, game)}
    save_receipt(db, user.id, f"dialogue:{sid}", idem, body.model_dump(), result)
    db.commit()
    start_task(run.id)
    return result


@router.get("/runs/{rid}")
def get_run(
    rid: str, db: Session = Depends(get_db), user: User = Depends(require_user)
):
    run = owned_run(db, rid, user.id)
    return {
        "id": run.id,
        "status": run.status,
        "events": run.events,
        "question": run.question,
        "actor_id": run.actor_id,
    }


@router.get("/runs/{rid}/events")
async def run_events(
    rid: str,
    request: Request,
    after: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    owned_run(db, rid, user.id)
    cursor = max(0, after)
    if request.headers.get("last-event-id"):
        try:
            cursor = max(cursor, int(request.headers["last-event-id"]))
        except ValueError:
            raise GameError("INVALID_CURSOR", "恢复游标无效。")
    owner = user.id

    async def events():
        nonlocal cursor
        heartbeat = time.monotonic()
        for _ in range(700):
            if await request.is_disconnected():
                break
            with SessionLocal() as fresh:
                try:
                    run = owned_run(fresh, rid, owner)
                except GameError:
                    return
                pending = [e for e in run.events if e["seq"] > cursor]
                terminal = run.status in TERMINAL
            for event in pending:
                cursor = event["seq"]
                yield f"id: {cursor}\nevent: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            if terminal:
                return
            if time.monotonic() - heartbeat > 10:
                yield ": heartbeat\n\n"
                heartbeat = time.monotonic()
            await asyncio.sleep(0.08)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/runs/{rid}/cancel")
async def cancel_run(
    rid: str, db: Session = Depends(get_db), user: User = Depends(require_user)
):
    owned_run(db, rid, user.id)
    owner = user.id
    db.close()
    cancel_task(rid)
    with SessionLocal() as fresh:
        status = owned_run(fresh, rid, owner).status
    return {"run_id": rid, "status": status}


@router.put("/sessions/{sid}/notes/{local_id}")
def save_note(
    sid: str,
    local_id: str,
    body: NoteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    game = owned_session(db, sid, user.id)
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", local_id):
        raise GameError("INVALID_ID", "笔记 ID 格式无效。")
    old = db.scalar(
        select(Note).where(Note.session_id == sid, Note.local_id == local_id)
    )
    if old and old.version != body.version:
        raise GameError(
            "NOTE_CONFLICT",
            "笔记已在另一处更新，请保留副本后合并。",
            409,
            {"server": note_view(old)},
        )
    if not old and body.version != 0:
        raise GameError("NOTE_CONFLICT", "笔记已被删除，请另存副本。", 409)
    known = set(game.state["evidence"]) | {s["id"] for s in game.state["statements"]}
    if not set(body.source_ids) <= known:
        raise GameError(
            "CONTENT_NOT_ACCESSIBLE", "笔记引用只能来自已发现证物或已交付证词。", 403
        )
    values = body.model_dump(exclude={"version"})
    values["updated_at"] = now()
    if old:
        changed = db.execute(
            update(Note)
            .where(Note.id == old.id, Note.version == body.version)
            .values(**values, version=body.version + 1)
        )
        if changed.rowcount != 1:
            raise GameError("NOTE_CONFLICT", "笔记有新的版本，请保留副本。", 409)
        db.expire(old)
        note = old
    else:
        note = Note(local_id=local_id, session_id=sid, **values)
        db.add(note)
    db.commit()
    return note_view(note)


@router.delete("/sessions/{sid}/notes/{local_id}")
def delete_note(
    sid: str,
    local_id: str,
    version: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    owned_session(db, sid, user.id)
    changed = db.execute(
        delete(Note).where(
            Note.session_id == sid, Note.local_id == local_id, Note.version == version
        )
    )
    if changed.rowcount != 1:
        raise GameError("NOTE_CONFLICT", "笔记版本已变化，请刷新后操作。", 409)
    db.commit()
    return {"ok": True}


@router.post("/sessions/{sid}/partner-analyses")
def partner(
    sid: str,
    body: PartnerRequest,
    idem: str = Header("", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    game = owned_session(db, sid, user.id)
    old = receipt(db, user.id, f"partner:{sid}", idem, body.model_dump())
    if old:
        return old
    check_active(db, game, body.expected_version)
    if game.state["hint_spent"] + body.level > 40:
        raise GameError("HINT_LIMIT", "本局搭档帮助额度已用完（40 点）。", 409)
    view = player_view(db, game)
    analysis = partner_from_projection(
        view, [n for n in view["notes"] if n["partner_allowed"]], body.level
    )
    new = deepcopy(game.state)
    new["partner_analyses"].append(analysis)
    new["hint_spent"] += body.level
    commit_state(
        db,
        game,
        new,
        "partner_analysis",
        {"level": body.level, "citation_count": len(analysis["citations"])},
    )
    result = {"analysis": analysis, "state": player_view(db, game)}
    save_receipt(db, user.id, f"partner:{sid}", idem, body.model_dump(), result)
    db.commit()
    return result


@router.post("/sessions/{sid}/submissions")
def submit(
    sid: str,
    body: Submission,
    idem: str = Header("", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    game = owned_session(db, sid, user.id)
    old = receipt(db, user.id, f"submit:{sid}", idem, body.model_dump())
    if old:
        return old
    check_active(db, game, body.expected_version)
    result = score_submission(content_for(db, game), game.state, body.model_dump())
    new = deepcopy(game.state)
    new["phase"] = "finished"
    new["result"] = result
    commit_state(db, game, new, "submitted", {"score": result["score"]})
    response = {"result": result, "state": player_view(db, game)}
    save_receipt(db, user.id, f"submit:{sid}", idem, body.model_dump(), response)
    db.commit()
    return response


@router.get("/sessions/{sid}/reveal")
def reveal(sid: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    game = owned_session(db, sid, user.id)
    if game.phase != "finished":
        raise GameError("REVEAL_LOCKED", "提交结案后才能查看真相。", 403)
    return game.state["result"]
