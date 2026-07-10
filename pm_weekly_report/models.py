from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EmailCategory(str, Enum):
    REQUIREMENT = "需求反馈"
    RISK = "风险"
    DECISION = "待决策"
    FYI = "FYI"
    REPLY_NEEDED = "待回复"
    OTHER = "其他"


class IMTag(str, Enum):
    REQUIREMENT = "需求"
    RISK = "风险"
    DECISION = "决策"
    TODO = "待办"


@dataclass
class EmailItem:
    subject: str
    sender: str
    date: datetime
    snippet: str
    category: EmailCategory
    product: str = ""
    message_id: str = ""


@dataclass
class IMMessage:
    platform: str
    group: str
    sender: str
    content: str
    timestamp: datetime
    tag: IMTag | None = None
    product: str = ""


@dataclass
class ProductProgress:
    product: str
    completed: str
    next_plan: str
    status: str
    risk: str
    owner: str = ""


@dataclass
class ActionItem:
    text: str
    assignee: str = ""
    due_date: str = ""
    source: str = ""


@dataclass
class WeeklyReportData:
    week_label: str
    date_range: str
    emails: list[EmailItem] = field(default_factory=list)
    requirements: list[IMMessage] = field(default_factory=list)
    risks: list[IMMessage] = field(default_factory=list)
    other_im_messages: list[IMMessage] = field(default_factory=list)
    progress: list[ProductProgress] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
