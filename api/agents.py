import asyncio
from copy import deepcopy

from sqlalchemy import select

from api.content import matches
from api.db import SessionLocal
from api.engine import TERMINAL, commit_state, content_for
from api.errors import GameError
from api.models import DialogueRun, GameSession, now
from api.providers import generate_approved

tasks: dict[str, asyncio.Task] = {}


def run_event(run, kind, **data):
    events = list(run.events)
    events.append({"seq": len(events) + 1, "type": kind, **data})
    run.events = events


def authorized_actor(case, state, aid):
    character = next(c for c in case["characters"] if c["id"] == aid)
    statements = [
        {
            "id": s["id"],
            "text": s["text"],
            "kind": s["kind"],
            "keywords": s["keywords"],
            "gated": s["condition"]["op"] != "always",
        }
        for s in character["statements"]
        if matches(s["condition"], state)
    ]
    actor = {k: character[k] for k in ["id", "name", "role", "personality"]}
    return actor, statements, deepcopy(state["characters"][aid]["questions"])


async def set_progress(rid, status):
    with SessionLocal() as db:
        run = db.get(DialogueRun, rid)
        if not run or run.status in TERMINAL:
            raise asyncio.CancelledError()
        run.status = status
        run_event(run, "run.status", status=status)
        db.commit()
    await asyncio.sleep(0.03)


def finish_run(rid, status, code=None):
    with SessionLocal() as db:
        run = db.get(DialogueRun, rid)
        if not run or run.status in TERMINAL:
            return
        game = db.get(GameSession, run.session_id)
        if not game:
            return
        state = deepcopy(game.state)
        if state.get("active_run") == rid:
            state["active_run"] = None
            commit_state(
                db, game, state, "dialogue_finished", {"run_id": rid, "status": status}
            )
        run.status = status
        run_event(run, "run." + status, status=status, code=code)
        db.commit()


async def execute_run(rid):
    try:
        with SessionLocal() as db:
            run = db.get(DialogueRun, rid)
            if not run or run.status in TERMINAL:
                return
            game = db.get(GameSession, run.session_id)
            actor, statements, memory = authorized_actor(
                content_for(db, game), game.state, run.actor_id
            )
            provider, owner, question = run.provider, game.owner_id, run.question
        approved = await asyncio.wait_for(
            generate_approved(
                provider,
                owner,
                actor,
                question,
                statements,
                memory,
                lambda status: set_progress(rid, status),
            ),
            timeout=45,
        )
        await set_progress(rid, "approved")
        for index, paragraph in enumerate(approved.paragraphs):
            await asyncio.sleep(
                __import__(
                    "api.settings", fromlist=["settings"]
                ).settings.delivery_delay
            )
            with SessionLocal() as db:
                run = db.get(DialogueRun, rid)
                if not run or run.status in TERMINAL:
                    return
                game = db.get(GameSession, run.session_id)
                if (
                    not game
                    or game.phase != "investigation"
                    or game.state.get("active_run") != rid
                ):
                    raise GameError("STATE_CONFLICT", "调查状态已变化。", 409)
                if game.version != run.base_version:
                    raise GameError(
                        "STATE_CONFLICT", "调查状态已变化，候选已丢弃。", 409
                    )
                state = deepcopy(game.state)
                _, current_statements, _ = authorized_actor(
                    content_for(db, game), state, run.actor_id
                )
                if index < len(approved.statements):
                    claim = approved.statements[index]
                    if claim["id"] not in {s["id"] for s in current_statements}:
                        raise GameError(
                            "CONTENT_NOT_ACCESSIBLE", "披露条件已变化。", 409
                        )
                    if claim["id"] not in {
                        s["id"] if isinstance(s, dict) else s
                        for s in state["statements"]
                    }:
                        state["statements"].append(
                            {
                                "id": claim["id"],
                                "text": claim["text"],
                                "actor_id": actor["id"],
                                "actor_name": actor["name"],
                                "kind": claim["kind"],
                                "run_id": rid,
                            }
                        )
                state["messages"].append(
                    {
                        "id": f"{rid}:{index}",
                        "run_id": rid,
                        "actor_id": actor["id"],
                        "actor_name": actor["name"],
                        "role": "assistant",
                        "text": paragraph,
                        "time": now(),
                    }
                )
                if index == 0:
                    astate = state["characters"][actor["id"]]
                    astate["questions"][question] = [
                        s["id"] for s in approved.statements
                    ]
                    astate["questions"] = dict(list(astate["questions"].items())[-24:])
                commit_state(
                    db,
                    game,
                    state,
                    "message_committed",
                    {"run_id": rid, "index": index},
                )
                run.base_version = game.version
                run.status = "delivering"
                run_event(
                    run,
                    "message.chunk",
                    index=index,
                    text=paragraph,
                    actor_id=actor["id"],
                )
                db.commit()
        finish_run(rid, "completed")
    except asyncio.CancelledError:
        finish_run(rid, "cancelled")
    except (TimeoutError, GameError) as exc:
        finish_run(rid, "failed", getattr(exc, "code", "MODEL_TIMEOUT"))
    except Exception:
        finish_run(rid, "failed", "RUN_FAILED")
    finally:
        tasks.pop(rid, None)


def start_task(rid):
    if rid not in tasks:
        tasks[rid] = asyncio.create_task(execute_run(rid))


def cancel_task(rid):
    finish_run(rid, "cancelled")
    if rid in tasks:
        tasks[rid].cancel()


def recover_interrupted():
    with SessionLocal() as db:
        ids = list(
            db.scalars(
                select(DialogueRun.id).where(DialogueRun.status.notin_(TERMINAL))
            )
        )
    for rid in ids:
        finish_run(rid, "expired", "SERVER_RESTARTED")
