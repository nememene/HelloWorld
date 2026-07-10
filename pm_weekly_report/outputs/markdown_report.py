from __future__ import annotations

from pm_weekly_report.models import EmailItem, IMMessage, ProductProgress, WeeklyReportData


def _format_email_line(item: EmailItem) -> str:
    prefix = f"[{item.product}] " if item.product else ""
    date_str = item.date.strftime("%m-%d")
    category = f" · {item.category.value}" if item.category.value != "其他" else ""
    snippet = f" — {item.snippet}" if item.snippet else ""
    return f"- {prefix}**{item.subject}** — {item.sender} · {date_str}{category}{snippet}"


def _format_im_line(msg: IMMessage) -> str:
    prefix = f"[{msg.product}] " if msg.product else ""
    date_str = msg.timestamp.strftime("%m-%d %H:%M")
    group = f"{msg.group} · " if msg.group else ""
    return f"- {prefix}{msg.content} — {group}{msg.sender} · {date_str}"


def render_markdown(data: WeeklyReportData, product_line_name: str) -> str:
    lines: list[str] = [
        f"# {product_line_name}周报 · {data.week_label}（{data.date_range}）",
        "",
        "## 一、本周重要邮件",
        "",
    ]

    if data.emails:
        for item in data.emails:
            lines.append(_format_email_line(item))
    else:
        lines.append("- 本周无匹配邮件，或邮箱采集未启用。")

    lines.extend(["", "## 二、群消息：需求与风险", "", "### 需求", ""])
    if data.requirements:
        for msg in data.requirements:
            lines.append(_format_im_line(msg))
    else:
        lines.append("- 本周暂无 `#需求` 标签或自动识别的需求消息。")

    lines.extend(["", "### 风险", ""])
    if data.risks:
        for msg in data.risks:
            lines.append(_format_im_line(msg))
    else:
        lines.append("- 本周暂无 `#风险` 标签或自动识别的风险消息。")

    if data.other_im_messages:
        lines.extend(["", "### 其他群消息", ""])
        for msg in data.other_im_messages[:10]:
            lines.append(_format_im_line(msg))

    lines.extend(["", "## 三、各产品进展", ""])
    if data.progress:
        lines.append("| 产品 | 本周完成 | 下周计划 | 状态 | 风险 | 负责人 |")
        lines.append("|------|----------|----------|------|------|--------|")
        for row in data.progress:
            lines.append(
                f"| {row.product} | {row.completed} | {row.next_plan} | "
                f"{row.status} | {row.risk or '—'} | {row.owner or '—'} |"
            )
    else:
        lines.append("- 未配置产品进展表，或 CSV 文件为空。")

    lines.extend(["", "## 四、待跟进事项", ""])
    if data.action_items:
        for item in data.action_items:
            meta: list[str] = []
            if item.assignee:
                meta.append(f"@{item.assignee}")
            if item.due_date:
                meta.append(item.due_date)
            if item.source:
                meta.append(item.source)
            suffix = f"（{' · '.join(meta)}）" if meta else ""
            lines.append(f"- [ ] {item.text}{suffix}")
    else:
        lines.append("- 本周未提取到明确待办。")

    lines.extend(["", "## 五、备注", "", "_可在此手动补充需要强调的内容。_", ""])
    return "\n".join(lines)
