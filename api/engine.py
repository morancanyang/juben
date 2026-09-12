"""Deterministic commands, transactionally committed snapshots and public projections."""

import hashlib
import json
from copy import deepcopy

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from api.content import matches
from api.errors import GameError
from api.models import (
    CommandReceipt,
    DialogueRun,
    GameSession,
    InvestigationEvent,
    Note,
    ScriptVersion,
    now,
)

TERMINAL = {"completed", "cancelled", "failed", "expired"}


def content_for(db: Session, game: GameSession):
    return db.get(ScriptVersion, game.script_version_id).content


def owned_session(db: Session, sid: str, owner: str):
    game = db.get(GameSession, sid)
    if not game or game.owner_id != owner:
        raise GameError("NOT_FOUND", "找不到这份卷宗。", 404)
    return game


def owned_run(db: Session, rid: str, owner: str):
    run = db.get(DialogueRun, rid)
    if not run:
        raise GameError("NOT_FOUND", "找不到这段对话。", 404)
    owned_session(db, run.session_id, owner)
    return run


def fingerprint(body: dict):
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def receipt(db: Session, owner: str, scope: str, key: str, body: dict):
    if not key or len(key) > 100:
        raise GameError("IDEMPOTENCY_REQUIRED", "操作缺少有效的幂等标识。")
    old = db.scalar(
        select(CommandReceipt).where(
            CommandReceipt.owner_id == owner,
            CommandReceipt.scope == scope,
            CommandReceipt.key == key,
        )
    )
    if old:
        if old.fingerprint != fingerprint(body):
            raise GameError(
                "IDEMPOTENCY_CONFLICT", "同一操作标识不能用于不同的请求。", 409
            )
        return old.result
    return None


def save_receipt(db, owner, scope, key, body, result):
    db.add(
        CommandReceipt(
            owner_id=owner,
            scope=scope,
            key=key,
            fingerprint=fingerprint(body),
            result=result,
        )
    )


def check_active(db: Session, game: GameSession, expected: int, *, check_busy=True):
    if game.version != expected:
        raise GameError(
            "STATE_CONFLICT",
            "调查进度已在另一页面更新，请刷新后重试。",
            409,
            {"version": game.version},
        )
    if game.phase != "investigation":
        raise GameError("CASE_CLOSED", "本局已结案，可在复盘后开启新一局。", 409)
    if check_busy and game.state.get("active_run"):
        raise GameError("RUN_BUSY", "请等待当前对话结束或先停止回答。", 409)


def commit_state(db: Session, game: GameSession, state: dict, kind: str, payload: dict):
    old_version = game.version
    timestamp = now()
    changed = db.execute(
        update(GameSession)
        .where(GameSession.id == game.id, GameSession.version == old_version)
        .values(
            state=state,
            version=old_version + 1,
            phase=state.get("phase", game.phase),
            updated_at=timestamp,
        ),
        execution_options={"synchronize_session": False},
    )
    if changed.rowcount != 1:
        db.rollback()
        raise GameError("STATE_CONFLICT", "操作与另一条调查记录冲突，请重试。", 409)
    db.add(
        InvestigationEvent(
            session_id=game.id, seq=old_version + 1, kind=kind, payload=payload
        )
    )
    db.expire(game)
    db.flush()


def initial_state(config: dict, case: dict):
    return {
        "phase": "investigation",
        "config": config,
        "evidence": [],
        "analyzed": [],
        "presented": [],
        "searched": [],
        "triggered": [],
        "visited": [case["scenes"][0]["id"]],
        "current_scene": case["scenes"][0]["id"],
        "points": 999
        if config["difficulty"] == "story"
        else 60
        if config["difficulty"] == "standard"
        else 40,
        "elapsed": 0,
        "messages": [],
        "statements": [],
        "partner_analyses": [],
        "hint_spent": 0,
        "characters": {
            c["id"]: {
                "trust": 40,
                "alertness": 10,
                "emotion": "平静",
                "questions": {},
                "observed": False,
            }
            for c in case["characters"]
        },
        "active_run": None,
        "result": None,
        "journal": [
            {"text": "调查开始。先勘查现场，再向相关人物求证。", "time": now()}
        ],
    }


def spend(state, amount=1):
    if state["points"] < amount:
        raise GameError(
            "NO_POINTS", "调查点已用完。你仍可整理笔记、使用搭档和提交结案。", 409
        )
    state["points"] -= amount
    state["elapsed"] += amount * 2


def add_evidence(state, eid):
    if eid not in state["evidence"]:
        state["evidence"].append(eid)


def apply_triggers(case, state):
    messages = []
    for _ in range(len(case["triggers"]) + 1):
        fired = False
        for trigger in case["triggers"]:
            if trigger["id"] not in state["triggered"] and matches(
                trigger["condition"], state
            ):
                state["triggered"].append(trigger["id"])
                add_evidence(state, trigger["evidence_id"])
                messages.append(trigger["message"])
                fired = True
        if not fired:
            break
    return messages


def take_action(case: dict, original: dict, command: dict):
    state = deepcopy(original)
    kind = command["type"]
    evidence_map = {e["id"]: e for e in case["evidence"]}
    actors = {c["id"]: c for c in case["characters"]}
    eid, aid = command.get("evidence_id"), command.get("actor_id")
    message = ""
    if kind in ["visit", "search"]:
        scene = next(
            (s for s in case["scenes"] if s["id"] == command["scene_id"]), None
        )
        if not scene or not matches(scene["condition"], state):
            raise GameError("CONTENT_NOT_ACCESSIBLE", "当前还不能调查这个地点。", 403)
        state["current_scene"] = scene["id"]
        if scene["id"] not in state["visited"]:
            state["visited"].append(scene["id"])
        if kind == "visit":
            message = f"来到{scene['name']}。"
        else:
            obj = next(
                (o for o in scene["objects"] if o["id"] == command["object_id"]), None
            )
            if not obj or not matches(obj["condition"], state):
                raise GameError(
                    "PREREQUISITE_REQUIRED",
                    "还缺少调查依据。先分析已发现的相关证物。",
                    409,
                )
            found_key = f"{scene['id']}:{obj['id']}"
            if found_key in state["searched"]:
                return state, "这里已经调查过，没有重复消耗调查点。"
            spend(state)
            state["searched"].append(found_key)
            add_evidence(state, obj["evidence_id"])
            message = f"发现证物：{evidence_map[obj['evidence_id']]['title']}。"
    elif kind in ["analyze", "present"]:
        if eid not in state["evidence"]:
            raise GameError("CONTENT_NOT_ACCESSIBLE", "你尚未发现这件证物。", 403)
        evidence = evidence_map[eid]
        if kind == "analyze":
            if eid in state["analyzed"]:
                return state, "这件证物已经分析过，没有重复消耗调查点。"
            spend(state)
            state["analyzed"].append(eid)
            message = evidence["analysis"]
        else:
            if aid not in actors:
                raise GameError("NOT_FOUND", "找不到这位角色。", 404)
            key = f"{eid}:{aid}"
            if key in state["presented"]:
                return state, "你已向该角色出示过此证物，可以继续追问。"
            spend(state)
            state["presented"].append(key)
            actor = state["characters"][aid]
            actor["trust"] = min(100, actor["trust"] + 8)
            actor["alertness"] = min(100, actor["alertness"] + 12)
            actor["emotion"] = (
                "有所迟疑" if aid in evidence["related_characters"] else "专注"
            )
            message = f"已向{actors[aid]['name']}出示{evidence['title']}。现在可以就证物追问。"
    elif kind == "combine":
        inputs = set(command["evidence_ids"])
        if not inputs <= set(state["evidence"]):
            raise GameError("CONTENT_NOT_ACCESSIBLE", "只能组合已发现的证物。", 403)
        combo = next(
            (c for c in case["combinations"] if set(c["inputs"]) == inputs), None
        )
        if not combo:
            raise GameError("NO_COMBINATION", "这些证物暂时无法形成新的证据链。", 409)
        if combo["output"] in state["evidence"]:
            return state, "这条证据链已经建立。"
        spend(state)
        add_evidence(state, combo["output"])
        state["analyzed"].append(combo["output"])
        message = f"建立证据链：{evidence_map[combo['output']]['title']}。"
    elif kind == "observe":
        if aid not in actors:
            raise GameError("NOT_FOUND", "找不到这位角色。", 404)
        actor = state["characters"][aid]
        if not actor["observed"]:
            spend(state)
            actor["observed"] = True
        message = f"{actors[aid]['name']}目前显得{actor['emotion']}。表情只能帮助决定追问方式，不能独立证明有罪。"
    triggered = apply_triggers(case, state)
    if triggered:
        message += " " + " ".join(triggered)
    state["journal"].append({"text": message, "time": now()})
    return state, message


def public_script(row: ScriptVersion, detail=False):
    case = row.content
    value = {
        k: case[k]
        for k in [
            "id",
            "title",
            "subtitle",
            "description",
            "genre",
            "difficulty",
            "duration",
            "cover",
            "tags",
            "warnings",
        ]
    }
    value.update(
        version=row.version,
        version_id=row.id,
        character_count=len(case["characters"]),
        evidence_count=len(case["evidence"]),
        custom=row.owner_id is not None,
    )
    if detail:
        value["intro"] = case["intro"]
        value["characters"] = [
            {k: c[k] for k in ["id", "name", "role", "bio", "color"]}
            for c in case["characters"]
        ]
    return value


def note_view(note: Note):
    return {
        "id": note.local_id,
        "version": note.version,
        "kind": note.kind,
        "text": note.text,
        "source_ids": note.source_ids,
        "partner_allowed": note.partner_allowed,
        "updated_at": note.updated_at,
    }


def player_view(db: Session, game: GameSession):
    case, state = content_for(db, game), game.state
    scenes = []
    for scene in case["scenes"]:
        unlocked = matches(scene["condition"], state)
        scenes.append(
            {
                "id": scene["id"],
                "name": scene["name"],
                "subtitle": scene["subtitle"],
                "unlocked": unlocked,
                "description": scene["description"]
                if unlocked
                else "调查相关证物后再来这里。",
                "objects": [
                    {
                        "id": o["id"],
                        "name": o["name"],
                        "description": o["description"],
                        "available": matches(o["condition"], state),
                        "searched": f"{scene['id']}:{o['id']}" in state["searched"],
                    }
                    for o in scene["objects"]
                ]
                if unlocked
                else [],
            }
        )
    evidence = []
    for e in case["evidence"]:
        if e["id"] in state["evidence"]:
            public = {
                k: e[k]
                for k in [
                    "id",
                    "title",
                    "type",
                    "description",
                    "source",
                    "time",
                    "related_characters",
                ]
            }
            public.update(
                analyzed=e["id"] in state["analyzed"],
                analysis=e["analysis"] if e["id"] in state["analyzed"] else None,
                presented_to=[
                    a["id"]
                    for a in case["characters"]
                    if f"{e['id']}:{a['id']}" in state["presented"]
                ],
            )
            evidence.append(public)
    characters = []
    for c in case["characters"]:
        public = {k: c[k] for k in ["id", "name", "role", "bio", "color"]}
        public.update(
            {
                k: state["characters"][c["id"]][k]
                for k in ["trust", "alertness", "emotion"]
            }
        )
        public["suggestions"] = ["案发时你在哪里？", "你观察到了什么异常？"]
        for s in c["statements"]:
            if s["condition"]["op"] != "always" and matches(s["condition"], state):
                public["suggestions"].append("能解释一下刚才出示的证物吗？")
                break
        characters.append(public)
    return {
        "id": game.id,
        "version": game.version,
        "phase": game.phase,
        "script": public_script(db.get(ScriptVersion, game.script_version_id), True),
        "config": state["config"],
        "points": state["points"],
        "elapsed": state["elapsed"],
        "current_scene": state["current_scene"],
        "scenes": scenes,
        "characters": characters,
        "evidence": evidence,
        "analyzed": state["analyzed"],
        "combinations": [
            c
            for c in case["combinations"]
            if set(c["inputs"]) <= set(state["evidence"])
        ],
        "messages": state["messages"],
        "statements": state["statements"],
        "journal": state["journal"][-80:],
        "notes": [
            note_view(n)
            for n in db.scalars(
                select(Note).where(Note.session_id == game.id).order_by(Note.updated_at)
            )
        ],
        "partner_analyses": state["partner_analyses"],
        "hint_spent": state["hint_spent"],
        "active_run": state["active_run"],
        "questions": case["questions"],
        "result": state["result"],
        "updated_at": game.updated_at,
    }


def score_submission(case: dict, state: dict, body: dict):
    selected = body["answers"]
    if set(selected) != set(case["answer"]):
        raise GameError("INCOMPLETE_REPORT", "请完成全部七项推理判断。")
    for q in case["questions"]:
        if selected[q["id"]] not in {o["id"] for o in q["options"]}:
            raise GameError("INVALID_OPTION", "推理选项无效，请刷新页面。")
    if not set(body["evidence_ids"]) <= set(state["evidence"]):
        raise GameError("CONTENT_NOT_ACCESSIBLE", "结案只能引用本局已发现的证物。", 403)
    weights = {
        "culprit": 30,
        "motive": 15,
        "method": 15,
        "time": 10,
        "location": 5,
        "tool": 5,
        "accomplice": 5,
    }
    breakdown = []
    for q in case["questions"]:
        correct = selected[q["id"]] == case["answer"][q["id"]]
        breakdown.append(
            {
                "id": q["id"],
                "label": q["label"],
                "earned": weights[q["id"]] if correct else 0,
                "maximum": weights[q["id"]],
                "correct": correct,
                "answer": case["answer"][q["id"]],
            }
        )
    coverage = len(set(body["evidence_ids"]) & set(case["key_evidence"])) / len(
        case["key_evidence"]
    )
    breakdown.append(
        {
            "id": "evidence",
            "label": "关键证据覆盖",
            "earned": round(coverage * 15),
            "maximum": 15,
            "correct": coverage == 1,
        }
    )
    total = sum(b["earned"] for b in breakdown)
    culprit_ok = selected["culprit"] == case["answer"]["culprit"]
    hidden = any(e["hidden"] and e["id"] in state["evidence"] for e in case["evidence"])
    if not culprit_ok:
        total = min(total, 49)
        ending = {
            "id": "mistaken",
            "title": "迷雾未散",
            "subtitle": "你的结论指向了错误的人。复盘证据，真相仍在等待。",
        }
    elif total >= 95 and hidden:
        ending = {
            "id": "hidden",
            "title": "暗处的回响",
            "subtitle": "你找到了凶手，也照亮了案件背后被藏起的秘密。",
        }
    elif total >= 85:
        ending = {
            "id": "solved",
            "title": "黎明之前",
            "subtitle": "证据终于连成完整的轮廓。你的判断让真相得以留下。",
        }
    else:
        ending = {
            "id": "partial",
            "title": "未完成的拼图",
            "subtitle": "你找到了关键人物，但动机、手法或证据仍有缺口。",
        }
    return {
        "score": total,
        "breakdown": breakdown,
        "ending": ending,
        "submitted": selected,
        "report": body["report"],
        "evidence_ids": body["evidence_ids"],
        "missed_evidence": [
            e["title"] for e in case["evidence"] if e["id"] not in state["evidence"]
        ],
        "truth": case["truth"],
        "hint_spent": state["hint_spent"],
        "elapsed": state["elapsed"],
        "finished_at": now(),
    }
