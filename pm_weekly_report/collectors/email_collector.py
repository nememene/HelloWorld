from __future__ import annotations

import email
import imaplib
import re
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime

from pm_weekly_report.models import EmailCategory, EmailItem


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


def _matches_filters(
    sender: str,
    subject: str,
    filters: dict,
) -> bool:
    exclude = filters.get("exclude_subject", [])
    if any(k.lower() in subject.lower() for k in exclude):
        return False

    domains = filters.get("domains", [])
    keywords = filters.get("subject_keywords", [])
    if not domains and not keywords:
        return True

    sender_lower = sender.lower()
    subject_lower = subject.lower()
    if domains and any(d.lower() in sender_lower for d in domains):
        return True
    if keywords and any(k.lower() in subject_lower for k in keywords):
        return True
    return not domains and not keywords


def fetch_emails(config: dict, week_start: datetime, week_end: datetime) -> list[EmailItem]:
    email_cfg = config.get("email", {})
    if not email_cfg.get("enabled"):
        return []

    username = email_cfg.get("username") or ""
    password = email_cfg.get("password") or ""
    if not username or not password:
        return []

    host = email_cfg["imap_host"]
    port = int(email_cfg.get("imap_port", 993))
    use_ssl = bool(email_cfg.get("use_ssl", True))
    mailbox = email_cfg.get("mailbox", "INBOX")
    filters = email_cfg.get("filters", {})

    if use_ssl:
        client = imaplib.IMAP4_SSL(host, port)
    else:
        client = imaplib.IMAP4(host, port)

    try:
        client.login(username, password)
        client.select(mailbox)
        since = (week_start - timedelta(days=1)).strftime("%d-%b-%Y")
        status, data = client.search(None, f'(SINCE "{since}")')
        if status != "OK":
            return []

        items: list[EmailItem] = []
        for num in data[0].split():
            status, msg_data = client.fetch(num, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            raw = msg_data[0][1]
            if not isinstance(raw, bytes):
                continue

            msg = email.message_from_bytes(raw)
            subject = _decode_mime_header(msg.get("Subject"))
            sender = _decode_mime_header(msg.get("From"))
            message_id = msg.get("Message-ID", f"local-{num.decode()}")

            date_header = msg.get("Date")
            try:
                msg_date = parsedate_to_datetime(date_header) if date_header else datetime.now()
                if msg_date.tzinfo:
                    msg_date = msg_date.replace(tzinfo=None)
            except (TypeError, ValueError):
                msg_date = datetime.now()

            if msg_date < week_start or msg_date > week_end:
                continue

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

            body = "\n".join(body_parts)[:500]
            if not _matches_filters(sender, subject, filters):
                continue

            snippet = body.strip().replace("\n", " ")[:160]
            category = classify_email(subject, body)
            product = _guess_product(subject, body)

            items.append(
                EmailItem(
                    subject=subject,
                    sender=sender,
                    date=msg_date,
                    snippet=snippet,
                    category=category,
                    product=product,
                    message_id=message_id,
                )
            )

        items.sort(key=lambda x: x.date, reverse=True)
        return items
    finally:
        try:
            client.logout()
        except Exception:
            pass
