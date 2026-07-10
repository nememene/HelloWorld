from __future__ import annotations

import email
import imaplib
import json
import os
import re
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path

from pm_weekly_report.models import EmailCategory, EmailItem


def dedupe_emails(items: list[EmailItem]) -> list[EmailItem]:
    seen: set[str] = set()
    unique: list[EmailItem] = []
    for item in items:
        key = item.message_id or f"{item.subject}|{item.sender}|{item.date.isoformat()}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def load_sample_emails(path: str, week_start: datetime, week_end: datetime) -> list[EmailItem]:
    file_path = Path(path)
    if not file_path.exists():
        return []

    with file_path.open(encoding="utf-8") as f:
        raw = json.load(f)

    items: list[EmailItem] = []
    for row in raw:
        msg_date = datetime.strptime(row["date"], "%Y-%m-%d %H:%M:%S")
        if msg_date < week_start or msg_date > week_end:
            continue
        items.append(
            EmailItem(
                subject=row["subject"],
                sender=row["sender"],
                date=msg_date,
                snippet=row.get("snippet", ""),
                category=EmailCategory(row.get("category", "其他")),
                product=row.get("product", ""),
                message_id=row.get("message_id", ""),
            )
        )
    return dedupe_emails(items)


def _decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for chunk, charset in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts)


def _guess_product(subject: str, body: str, products: list[str] | None = None) -> str:
    text = f"{subject} {body}"
    for product in products or []:
        if product in text:
            return product
    match = re.search(r"\[([^\]]+)\]", subject)
    return match.group(1) if match else ""


def classify_email(subject: str, body: str) -> EmailCategory:
    text = f"{subject} {body}".lower()
    rules: list[tuple[EmailCategory, list[str]]] = [
        (EmailCategory.RISK, ["风险", "延期", "阻塞", "故障", "投诉", "紧急", "risk", "blocker"]),
        (EmailCategory.REQUIREMENT, ["需求", "功能", "希望", "建议", "反馈", "feature", "request"]),
        (EmailCategory.DECISION, ["决策", "确认", "审批", "是否", "请定", "approve"]),
        (EmailCategory.REPLY_NEEDED, ["请回复", "待回复", "请确认", "reply", "action required"]),
        (EmailCategory.FYI, ["通知", "公告", "fyi", "仅供参考"]),
    ]
    for category, keywords in rules:
        if any(k in text for k in keywords):
            return category
    return EmailCategory.OTHER


def _matches_filters(sender: str, subject: str, body: str, filters: dict) -> bool:
    exclude = filters.get("exclude_subject", [])
    text = f"{subject} {body}"
    if any(k.lower() in text.lower() for k in exclude):
        return False

    if filters.get("include_all", False):
        return True

    domains = filters.get("domains", [])
    keywords = filters.get("subject_keywords", [])
    match_body = filters.get("match_body", True)

    if not domains and not keywords:
        return True

    sender_lower = sender.lower()
    subject_lower = subject.lower()
    body_lower = body.lower()

    if domains and any(d.lower() in sender_lower for d in domains):
        return True
    if keywords:
        for k in keywords:
            kw = k.lower()
            if kw in subject_lower or (match_body and kw in body_lower):
                return True
    return False


def _parse_msg_date(date_header: str | None) -> datetime:
    try:
        msg_date = parsedate_to_datetime(date_header) if date_header else datetime.now()
        if msg_date.tzinfo:
            msg_date = msg_date.astimezone().replace(tzinfo=None)
        return msg_date
    except (TypeError, ValueError):
        return datetime.now()


def _extract_body(msg: email.message.Message) -> str:
    body_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode(errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_parts.append(payload.decode(errors="replace"))
    return "\n".join(body_parts)[:500]


def _search_message_ids(client: imaplib.IMAP4, email_cfg: dict, week_start: datetime) -> list[bytes]:
    fetch_mode = email_cfg.get("fetch_mode", "recent")
    scan_limit = int(email_cfg.get("scan_limit", 300))

    if fetch_mode == "since":
        since = (week_start - timedelta(days=1)).strftime("%d-%b-%Y")
        status, data = client.search(None, f'(SINCE "{since}")')
        if status != "OK" or not data or not data[0]:
            status, data = client.search(None, "ALL")
    else:
        status, data = client.search(None, "ALL")

    if status != "OK" or not data or not data[0]:
        return []

    ids = [i for i in data[0].split() if i]
    if fetch_mode == "recent" and len(ids) > scan_limit:
        ids = ids[-scan_limit:]
    return ids


def _parse_message(raw: bytes, num: bytes, week_start: datetime, week_end: datetime, filters: dict) -> EmailItem | None:
    msg = email.message_from_bytes(raw)
    subject = _decode_mime_header(msg.get("Subject"))
    sender = _decode_mime_header(msg.get("From"))
    message_id = msg.get("Message-ID", f"local-{num.decode()}")
    msg_date = _parse_msg_date(msg.get("Date"))

    if msg_date < week_start or msg_date > week_end:
        return None

    body = _extract_body(msg)
    if not _matches_filters(sender, subject, body, filters):
        return None

    snippet = body.strip().replace("\n", " ")[:160]
    return EmailItem(
        subject=subject,
        sender=sender,
        date=msg_date,
        snippet=snippet,
        category=classify_email(subject, body),
        product=_guess_product(subject, body),
        message_id=message_id,
    )


def fetch_emails(
    config: dict,
    week_start: datetime,
    week_end: datetime,
    verbose: bool = False,
) -> list[EmailItem]:
    email_cfg = config.get("email", {})
    username = email_cfg.get("username") or os.getenv("EMAIL_USER", "")
    password = email_cfg.get("password") or os.getenv("EMAIL_PASSWORD", "")
    if not username or not password:
        if verbose:
            print("[email] 未配置用户名或密码，跳过拉取")
        return []

    host = email_cfg["imap_host"]
    port = int(email_cfg.get("imap_port", 993))
    use_ssl = bool(email_cfg.get("use_ssl", True))
    mailbox = email_cfg.get("mailbox", "INBOX")
    filters = email_cfg.get("filters", {})
    max_emails = int(email_cfg.get("max_emails", 50))

    if use_ssl:
        client = imaplib.IMAP4_SSL(host, port, timeout=30)
    else:
        client = imaplib.IMAP4(host, port, timeout=30)

    try:
        client.login(username, password)
        client.select(mailbox)
        ids = _search_message_ids(client, email_cfg, week_start)
        if verbose:
            print(f"[email] 扫描邮件 ID 数量: {len(ids)}，本周范围: {week_start.date()} ~ {week_end.date()}")

        items: list[EmailItem] = []
        in_week = 0
        for num in ids:
            status, msg_data = client.fetch(num, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, bytes):
                continue

            parsed = _parse_message(raw, num, week_start, week_end, filters)
            if parsed is None:
                continue
            in_week += 1
            items.append(parsed)

        if verbose:
            print(f"[email] 本周匹配邮件: {in_week}，过滤后纳入周报: {len(items)}")

        items.sort(key=lambda x: x.date, reverse=True)
        return dedupe_emails(items)[:max_emails]
    finally:
        try:
            client.logout()
        except Exception:
            pass


def collect_emails(
    config: dict,
    week_start: datetime,
    week_end: datetime,
    verbose: bool = False,
) -> list[EmailItem]:
    email_cfg = config.get("email", {})
    sample_file = email_cfg.get("sample_file", "data/sample_emails.json")
    use_sample = email_cfg.get("use_sample_when_disabled", True)

    if email_cfg.get("enabled"):
        emails = fetch_emails(config, week_start, week_end, verbose=verbose)
        if emails:
            return emails
        if verbose:
            print("[email] 未拉取到本周邮件（请检查 fetch_mode / 日期范围 / 过滤规则）")

    if use_sample and not email_cfg.get("enabled"):
        return load_sample_emails(sample_file, week_start, week_end)
    return []
