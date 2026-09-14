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

# Private cognitive profiles keep the model from treating every NPC as the
# same narrator.  These fields are deliberately separate from the public bio:
# they describe motives and conversational tactics the player can infer over
# time, while the authorization gate still controls which facts may be said.
AGENT_PROFILES = {
    "lin": {"goal": "保护山庄声誉并掩饰自己曾替顾衡付款的经历", "fear": "被当成封口费的共犯", "stance": "知道顾衡的习惯，愿意保护他但不愿牺牲自己", "voice": "短句、克制、先说观察再解释；被追问时会改用更具体的时间", "rapport": "初始礼貌但紧张"},
    "zhou": {"goal": "维护医师专业信誉并控制死亡诊断的解释权", "fear": "医疗箱和处方被误读为作案证据", "stance": "相信检查记录胜过传闻，对顾衡有私人责任感", "voice": "专业、疏离、使用医学术语；重复追问时更简短", "rapport": "初始客气而有距离"},
    "xu": {"goal": "证明自己没有因合同争执而报复顾衡", "fear": "修复合同丢失让他成为替罪羊", "stance": "对顾衡不满但重视器物事实，愿意指出别人忽略的细节", "voice": "直率、带轻微讽刺，常用器物比喻；不喜欢空泛指控", "rapport": "初始防备，认可具体证据"},
    "he": {"goal": "维持乘务秩序并让巡查记录经得起复核", "fear": "乘客安全事故追责", "stance": "把流程和时间表当作可信依据，不替任何乘客站队", "voice": "干练、按时间顺序回答，喜欢说‘按流程’；被质疑会逐项核对", "rapport": "初始职业性合作"},
    "shen": {"goal": "保护公司和个人签批记录不被公开", "fear": "匿名材料与门禁卡把他和记者联系起来", "stance": "知道商业纠纷的关键部分，努力把事实说成巧合", "voice": "沉稳精确，回避动机词；压力升高时句子更短、反问更多", "rapport": "初始冷淡戒备"},
    "qiao": {"goal": "安全离开列车并证明自己没有凭空猜测", "fear": "自己的耳机和时间记录被认为不可靠", "stance": "只提供亲耳听见或亲眼看见的细节，不替别人下结论", "voice": "有停顿、会自我修正，先说‘我听见/看见’再给判断", "rapport": "初始紧张但愿意合作"},
    "su": {"goal": "控制权限系统叙事并保住研究项目", "fear": "日志签名和令牌记录暴露她的操作", "stance": "相信技术细节能划清责任，面对证据会重新定义问题", "voice": "冷静、技术化、偏好限定条件；警觉时纠正术语而非直接否认", "rapport": "初始理性疏离"},
    "lu": {"goal": "保全原始数据并让论文成果不被抹掉", "fear": "被旧日学术冲突牵连成报复者", "stance": "对韩川有怨气但优先相信可重复的数据", "voice": "严谨、引用记录和样本，偶尔流露不满；不接受无来源推断", "rapport": "初始冷静审慎"},
    "bai": {"goal": "守住医学判断和站内人员的生还机会", "fear": "有人用终端记录否定真实死亡时间", "stance": "同情死者也保护患者隐私，只区分体征与推测", "voice": "温和准确，明确区分观察、诊断和猜测；压力下更坚定", "rapport": "初始温和专业"},
}


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
    actor["agent_profile"] = deepcopy(AGENT_PROFILES.get(aid, {
        # Author-created scripts still receive a distinct profile derived from
        # their identity, so adding an NPC never silently falls back to a
        # shared personality.
        "goal": f"履行{character['role']}职责并保护自己的选择",
        "fear": f"因{character['role']}相关责任被错误归责",
        "stance": f"以{character['name']}亲历的细节和已核实证据为准",
        "voice": f"保持{character['personality']}的表达，先陈述观察再表达判断",
        "rapport": "初始谨慎",
    }))
    astate = state["characters"][aid]
    actor["relationship_state"] = {
        "trust": astate.get("trust", 40),
        "alertness": astate.get("alertness", 10),
        "emotion": astate.get("emotion", "平静"),
    }
    memory = deepcopy(astate.get("questions", {}))
    memory["_agent_memory"] = deepcopy(astate.get("agent_memory", {}))
    return actor, statements, memory


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
            history = [{"role": m["role"], "text": m["text"]} for m in game.state.get("messages", []) if m.get("actor_id") == run.actor_id]
            case = content_for(db, game)
            scene = next((s for s in case["scenes"] if s["id"] == game.state.get("current_scene")), None)
            context = {
                "case_title": case.get("title"),
                "scene": {"id": scene.get("id"), "name": scene.get("name"), "description": scene.get("description")} if scene else {},
                "known_evidence": [e for e in game.state.get("evidence", [])],
                "analyzed_evidence_ids": game.state.get("analyzed", []),
                "elapsed_minutes": game.state.get("elapsed", 0),
            }
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
                history,
                context,
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
