from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from pm_weekly_report.models import IMMessage, IMTag


TAG_PATTERN = re.compile(r"#(需求|风险|决策|待办)")
PRODUCT_PATTERN = re.compile(r"\[([^\]]+)\]")


def _parse_tag(content: str) -> IMTag | None:
    match = TAG_PATTERN.search(content)
    if not match:
        return None
    mapping = {
        "需求": IMTag.REQUIREMENT,
        "风险": IMTag.RISK,
        "决策": IMTag.DECISION,
        "待办": IMTag.TODO,
    }
    return mapping.get(match.group(1))


def _guess_tag_from_content(content: str) -> IMTag | None:
    lowered = content.lower()
    if any(k in lowered for k in ["风险", "延期", "阻塞", "故障", "投诉"]):
        return IMTag.RISK
    if any(k in lowered for k in ["需求", "希望", "功能", "反馈", "建议"]):
        return IMTag.REQUIREMENT
    if any(k in lowered for k in ["决策", "确认", "定稿"]):
        return IMTag.DECISION
    if any(k in lowered for k in ["待办", "跟进", "负责"]):
        return IMTag.TODO
    return None


def _parse_product(content: str) -> str:
    match = PRODUCT_PATTERN.search(content)
    return match.group(1) if match else ""


def _parse_timestamp(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.now()


def load_im_messages(
    messages_file: str | Path,
    week_start: datetime,
    week_end: datetime,
) -> list[IMMessage]:
    path = Path(messages_file)
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    messages: list[IMMessage] = []
    for item in raw:
        ts = _parse_timestamp(item.get("timestamp", ""))
        if ts < week_start or ts > week_end:
            continue

        content = item.get("content", "").strip()
        tag = _parse_tag(content) or _guess_tag_from_content(content)
        product = item.get("product") or _parse_product(content)

        messages.append(
            IMMessage(
                platform=item.get("platform", "unknown"),
                group=item.get("group", ""),
                sender=item.get("sender", ""),
                content=content,
                timestamp=ts,
                tag=tag,
                product=product,
            )
        )

    messages.sort(key=lambda m: m.timestamp, reverse=True)
    return messages


def split_im_messages(messages: list[IMMessage]) -> tuple[list[IMMessage], list[IMMessage], list[IMMessage]]:
    requirements: list[IMMessage] = []
    risks: list[IMMessage] = []
    others: list[IMMessage] = []

    for msg in messages:
        if msg.tag == IMTag.REQUIREMENT:
            requirements.append(msg)
        elif msg.tag == IMTag.RISK:
            risks.append(msg)
        else:
            others.append(msg)

    return requirements, risks, others
