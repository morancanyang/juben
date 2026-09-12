"""Versioned content contract. All answers stay in this server-side package."""

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Condition(StrictModel):
    op: Literal[
        "always",
        "all",
        "any",
        "not",
        "hasEvidence",
        "analyzed",
        "presented",
        "trust",
        "phase",
        "time",
    ] = "always"
    ref: str = ""
    actor: str = ""
    value: int | str = 0
    children: list["Condition"] = Field(default_factory=list, max_length=12)


def matches(rule: dict, state: dict, depth: int = 0) -> bool:
    if depth > 12:
        return False
    op, ref = rule.get("op", "always"), rule.get("ref", "")
    children = rule.get("children", [])
    if op == "always":
        return True
    if op == "all":
        return all(matches(c, state, depth + 1) for c in children)
    if op == "any":
        return any(matches(c, state, depth + 1) for c in children)
    if op == "not":
        return len(children) == 1 and not matches(children[0], state, depth + 1)
    if op == "hasEvidence":
        return ref in state["evidence"]
    if op == "analyzed":
        return ref in state["analyzed"]
    if op == "presented":
        return f"{ref}:{rule.get('actor')}" in state["presented"]
    if op == "trust":
        return state["characters"].get(rule.get("actor"), {}).get("trust", 0) >= int(
            rule.get("value", 0)
        )
    if op == "phase":
        return state.get("phase") == rule.get("value")
    if op == "time":
        return state.get("elapsed", 0) >= int(rule.get("value", 0))
    return False


class Statement(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    text: str = Field(min_length=1, max_length=600)
    keywords: list[str] = Field(default_factory=list)
    condition: Condition = Field(default_factory=Condition)
    kind: Literal["statement", "fact"] = "statement"


class Character(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    name: str = Field(min_length=1, max_length=30)
    role: str = Field(max_length=60)
    bio: str = Field(max_length=500)
    personality: str = Field(max_length=300)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    statements: list[Statement] = Field(min_length=1, max_length=30)


class InvestigationObject(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    name: str = Field(max_length=60)
    description: str = Field(max_length=400)
    evidence_id: str
    condition: Condition = Field(default_factory=Condition)


class Scene(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    name: str = Field(max_length=60)
    subtitle: str = Field(max_length=80)
    description: str = Field(max_length=1000)
    condition: Condition = Field(default_factory=Condition)
    objects: list[InvestigationObject] = Field(min_length=1, max_length=20)


class Evidence(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    title: str = Field(max_length=80)
    type: Literal["document", "object", "trace", "record", "deduction"]
    description: str = Field(max_length=1000)
    analysis: str = Field(max_length=1200)
    source: str = Field(max_length=80)
    time: str = Field(max_length=50)
    related_characters: list[str] = Field(default_factory=list)
    hidden: bool = False


class Combination(StrictModel):
    inputs: list[str] = Field(min_length=2, max_length=4)
    output: str
    label: str = Field(max_length=80)


class Trigger(StrictModel):
    id: str
    condition: Condition
    evidence_id: str
    message: str = Field(max_length=400)


class Choice(StrictModel):
    id: str
    label: str = Field(max_length=120)


class Question(StrictModel):
    id: Literal["culprit", "motive", "method", "time", "location", "tool", "accomplice"]
    label: str
    options: list[Choice] = Field(min_length=2, max_length=10)


class TruthChapter(StrictModel):
    title: str = Field(max_length=80)
    text: str = Field(max_length=3000)


class CasePackage(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    title: str = Field(min_length=2, max_length=60)
    subtitle: str = Field(max_length=100)
    description: str = Field(min_length=10, max_length=1200)
    intro: str = Field(min_length=10, max_length=2000)
    genre: str = Field(max_length=30)
    difficulty: Literal["入门", "进阶", "烧脑"]
    duration: int = Field(ge=10, le=240)
    cover: Literal["manor", "train", "station"]
    tags: list[str] = Field(min_length=1, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=8)
    characters: list[Character] = Field(min_length=2, max_length=8)
    scenes: list[Scene] = Field(min_length=1, max_length=10)
    evidence: list[Evidence] = Field(min_length=3, max_length=60)
    combinations: list[Combination] = Field(default_factory=list, max_length=20)
    triggers: list[Trigger] = Field(default_factory=list, max_length=20)
    questions: list[Question] = Field(min_length=7, max_length=7)
    answer: dict[str, str]
    key_evidence: list[str] = Field(min_length=2)
    truth: list[TruthChapter] = Field(min_length=3, max_length=10)


def checksum(content: dict) -> str:
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def validate_package(raw: Any) -> tuple[dict | None, list[dict]]:
    issues = []
    try:
        content = CasePackage.model_validate(raw).model_dump()
    except Exception as exc:
        errors = (
            exc.errors()
            if hasattr(exc, "errors")
            else [{"loc": (), "msg": "无效 JSON 内容"}]
        )
        return None, [
            {
                "severity": "blocker",
                "path": ".".join(map(str, e["loc"])),
                "message": e["msg"],
            }
            for e in errors[:30]
        ]

    def issue(path, message):
        issues.append({"severity": "blocker", "path": path, "message": message})

    entities = ["characters", "scenes", "evidence", "triggers", "questions"]
    for key in entities:
        ids = [x["id"] for x in content[key]]
        if len(ids) != len(set(ids)):
            issue(key, "同类对象 ID 不得重复")
    eids = {x["id"] for x in content["evidence"]}
    actors = {x["id"] for x in content["characters"]}

    def check_rule(rule, path, depth=0):
        if depth > 10:
            issue(path, "条件嵌套超过 10 层")
            return
        if (
            rule["op"] in ["hasEvidence", "analyzed", "presented"]
            and rule["ref"] not in eids
        ):
            issue(path, "条件引用了不存在的证物")
        if rule["op"] in ["presented", "trust"] and rule["actor"] not in actors:
            issue(path, "条件引用了不存在的角色")
        if rule["op"] in ["trust", "time"] and not isinstance(rule["value"], int):
            issue(path, "信任或时间条件必须使用整数")
        if rule["op"] == "not" and len(rule["children"]) != 1:
            issue(path, "not 条件必须恰有一个子条件")
        for child in rule["children"]:
            check_rule(child, path, depth + 1)

    def walk(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "condition":
                    check_rule(value, path)
                else:
                    walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}.{i}")

    walk(content)
    statement_ids = []
    for actor in content["characters"]:
        statement_ids += [s["id"] for s in actor["statements"]]
    if len(statement_ids) != len(set(statement_ids)):
        issue("characters", "证词 ID 必须在整个剧本中唯一")
    for scene in content["scenes"]:
        object_ids = [o["id"] for o in scene["objects"]]
        if len(object_ids) != len(set(object_ids)):
            issue(f"scenes.{scene['id']}", "场景对象 ID 重复")
        for obj in scene["objects"]:
            if obj["evidence_id"] not in eids:
                issue(f"scenes.{scene['id']}", "调查对象引用了不存在的证物")
    for e in content["evidence"]:
        if not set(e["related_characters"]) <= actors:
            issue(f"evidence.{e['id']}", "证物关联了不存在的角色")
    for c in content["combinations"]:
        if not set(c["inputs"] + [c["output"]]) <= eids:
            issue("combinations", "组合规则引用不存在的证物")
    for t in content["triggers"]:
        if t["evidence_id"] not in eids:
            issue("triggers", "事件引用不存在的证物")
    fields = {"culprit", "motive", "method", "time", "location", "tool", "accomplice"}
    if (
        set(content["answer"]) != fields
        or {q["id"] for q in content["questions"]} != fields
    ):
        issue("answer", "必须包含凶手、动机、手法、时间、地点、工具、共犯七项")
    for q in content["questions"]:
        if content["answer"].get(q["id"]) not in [o["id"] for o in q["options"]]:
            issue(f"questions.{q['id']}", "标准答案必须存在于固定选项中")
    if not set(content["key_evidence"]) <= eids:
        issue("key_evidence", "关键证据引用无效")
    if content["answer"].get("culprit") not in actors:
        issue("answer.culprit", "凶手必须为现有角色")
    # Conservative monotonic reachability; non-monotonic author rules require manual review.
    reached = set()
    state = {
        "evidence": [],
        "analyzed": [],
        "presented": [],
        "characters": {a: {"trust": 100} for a in actors},
        "phase": "investigation",
        "elapsed": 999,
    }
    if not issues:
        for _ in range(len(eids) + 1):
            before = set(reached)
            state.update(
                evidence=list(reached),
                analyzed=list(reached),
                presented=[f"{e}:{a}" for e in reached for a in actors],
            )
            for scene in content["scenes"]:
                if matches(scene["condition"], state):
                    reached.update(
                        o["evidence_id"]
                        for o in scene["objects"]
                        if matches(o["condition"], state)
                    )
            for combo in content["combinations"]:
                if set(combo["inputs"]) <= reached:
                    reached.add(combo["output"])
            for trigger in content["triggers"]:
                if matches(trigger["condition"], state):
                    reached.add(trigger["evidence_id"])
            if before == reached:
                break
        for missing in set(content["key_evidence"]) - reached:
            issue(f"evidence.{missing}", "关键证物不可达：检查前置条件或循环依赖")
    issues.append(
        {
            "severity": "suggestion",
            "path": "truth",
            "message": "规则校验不等于文学逻辑验证。启用前请试玩成功、误判和替代调查路径。",
        }
    )
    return content, issues
