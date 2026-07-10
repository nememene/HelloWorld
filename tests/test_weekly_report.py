from __future__ import annotations

from datetime import datetime

from pm_weekly_report.collectors.email_collector import collect_emails, dedupe_emails, load_sample_emails
from pm_weekly_report.collectors.im_collector import load_im_messages, split_im_messages
from pm_weekly_report.collectors.progress_collector import load_progress_csv
from pm_weekly_report.config import load_config
from pm_weekly_report.models import EmailItem, EmailCategory
from pm_weekly_report.outputs.markdown_report import render_markdown
from pm_weekly_report.processors.action_extractor import extract_action_items, get_week_range
from pm_weekly_report.__main__ import build_report


def test_get_week_range():
    ref = datetime(2026, 7, 10)
    start, end, label, date_range = get_week_range(ref)
    assert start.weekday() == 0
    assert end.weekday() == 6
    assert "2026" in label
    assert "~" in date_range


def test_get_week_range_by_iso_week():
    start, end, label, _ = get_week_range(iso_week=28, iso_year=2026)
    assert start.month == 7
    assert "28" in label


def test_load_im_messages_and_split():
    start = datetime(2026, 7, 6)
    end = datetime(2026, 7, 12, 23, 59, 59)
    messages = load_im_messages("data/im_messages.json", start, end)
    assert len(messages) == 5
    requirements, risks, decisions, others = split_im_messages(messages)
    assert len(requirements) == 1
    assert len(risks) == 2
    assert len(decisions) == 1


def test_load_sample_emails():
    start = datetime(2026, 7, 6)
    end = datetime(2026, 7, 12, 23, 59, 59)
    emails = load_sample_emails("data/sample_emails.json", start, end)
    assert len(emails) == 3
    assert emails[0].category == EmailCategory.REQUIREMENT


def test_email_dedupe():
    items = [
        EmailItem("a", "b", datetime.now(), "", EmailCategory.OTHER, message_id="id-1"),
        EmailItem("a", "b", datetime.now(), "", EmailCategory.OTHER, message_id="id-1"),
    ]
    assert len(dedupe_emails(items)) == 1


def test_load_progress_csv():
    rows = load_progress_csv("data/product_progress.csv")
    assert len(rows) == 3
    assert rows[0].product == "产品A"


def test_build_report_with_sample_data():
    config = load_config("config.example.yaml")
    data = build_report(config, reference=datetime(2026, 7, 10))
    assert data.week_label
    assert len(data.progress) == 3
    assert len(data.emails) == 3
    assert len(data.requirements) >= 1
    assert len(data.risks) >= 1
    assert len(data.decisions) >= 1


def test_render_markdown_contains_sections():
    config = load_config("config.example.yaml")
    data = build_report(config, reference=datetime(2026, 7, 10))
    md = render_markdown(data, "核心产品线")
    assert "## 一、本周重要邮件" in md
    assert "## 二、群消息：需求与风险" in md
    assert "### 决策" in md
    assert "## 三、各产品进展" in md
    assert "## 四、待跟进事项" in md
    assert "产品A" in md
    assert "批量导出" in md


def test_collect_emails_uses_sample_when_disabled():
    config = load_config("config.example.yaml")
    start = datetime(2026, 7, 6)
    end = datetime(2026, 7, 12, 23, 59, 59)
    emails = collect_emails(config, start, end)
    assert len(emails) == 3


def test_extract_action_items():
    start = datetime(2026, 7, 6)
    end = datetime(2026, 7, 12, 23, 59, 59)
    messages = load_im_messages("data/im_messages.json", start, end)
    items = extract_action_items([], messages)
    assert any("定价页" in i.text for i in items)
