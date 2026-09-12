from typing import Literal

from pydantic import Field

from api.content import StrictModel


class StartSession(StrictModel):
    script_id: str
    difficulty: Literal["story", "standard", "expert"] = "standard"
    perspective: Literal["侦探", "记者", "法医"] = "侦探"
    partner_style: Literal["逻辑", "质疑", "陪伴", "法证"] = "逻辑"


class Versioned(StrictModel):
    expected_version: int = Field(ge=1)


class Action(Versioned):
    type: Literal["search", "analyze", "present", "combine", "observe", "visit"]
    scene_id: str = ""
    object_id: str = ""
    evidence_id: str = ""
    actor_id: str = ""
    evidence_ids: list[str] = Field(default_factory=list, max_length=4)


class DialogueRequest(Versioned):
    actor_id: str
    question: str = Field(min_length=1, max_length=1200)


class NoteRequest(StrictModel):
    version: int = Field(ge=0)
    kind: Literal["fact", "statement", "inference", "hypothesis"] = "hypothesis"
    text: str = Field(max_length=8000)
    source_ids: list[str] = Field(default_factory=list, max_length=20)
    partner_allowed: bool = True


class PartnerRequest(Versioned):
    level: int = Field(ge=1, le=4)


class Submission(Versioned):
    answers: dict[str, str]
    evidence_ids: list[str] = Field(max_length=60)
    report: str = Field(default="", max_length=8000)


class Credentials(StrictModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_]{3,32}$")
    password: str = Field(min_length=8, max_length=128)


class Preferences(StrictModel):
    nickname: str = Field(min_length=1, max_length=30)
    provider: Literal["mock", "openai", "deepseek"] = "mock"
    theme: Literal["dark", "light"] = "dark"
    font_size: Literal["normal", "large"] = "normal"


class DraftRequest(StrictModel):
    content: dict


class IdeaRequest(StrictModel):
    title: str = Field(min_length=2, max_length=50)
    setting: str = Field(min_length=5, max_length=600)
