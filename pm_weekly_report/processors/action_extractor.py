from __future__ import annotations

import re
from datetime import datetime, timedelta

from pm_weekly_report.models import ActionItem, EmailItem, IMMessage


ACTION_PATTERN = re.compile(
    r"#待办\s*(.+?)(?:\s+@(\S+))?(?:\s+(\d{4}-\d{2}-\d{2}))?$",
    re.IGNORECASE,
)
INLINE_TODO_PATTERN = re.compile(
    r"(?:待办|跟进)[:：]\s*(.+?)(?:\s+@(\S+))?(?:\s+(\d{4}-\d{2}-\d{2}))?",
    re.IGNORECASE,
)


def get_week_range(
    reference: datetime | None = None,
    iso_week: int | None = None,
    iso_year: int | None = None,
) -> tuple[datetime, datetime, str, str]:
    if iso_week is not None:
        year = iso_year or datetime.now().year
        week_start = datetime.fromisocalendar(year, iso_week, 1)
    else:
        ref = reference or datetime.now()
        week_start = (ref - timedelta(days=ref.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    week_end = (week_start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=0)
    cal_year, cal_week, _ = week_start.isocalendar()
    week_label = f"{cal_year} 第 {cal_week} 周"
    date_range = f"{week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}"
    return week_start, week_end, week_label, date_range


def extract_action_items(emails: list[EmailItem], im_messages: list[IMMessage]) -> list[ActionItem]:
    items: list[ActionItem] = []

    for msg in im_messages:
        for pattern in (ACTION_PATTERN, INLINE_TODO_PATTERN):
            match = pattern.search(msg.content)
            if match:
                items.append(
                    ActionItem(
                        text=match.group(1).strip(),
                        assignee=(match.group(2) or "").strip(),
                        due_date=(match.group(3) or "").strip(),
                        source=f"{msg.platform}/{msg.group}",
                    )
                )
                break

    for mail in emails:
        if mail.category.value in {"待回复", "待决策"}:
            items.append(
                ActionItem(
                    text=f"回复邮件：{mail.subject}",
                    assignee="",
                    due_date="",
                    source=mail.sender,
                )
            )

    seen: set[str] = set()
    unique: list[ActionItem] = []
    for item in items:
        key = f"{item.text}|{item.assignee}|{item.due_date}"
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
