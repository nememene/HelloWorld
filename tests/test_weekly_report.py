from __future__ import annotations

from datetime import datetime

from pm_weekly_report.collectors.im_collector import load_im_messages, split_im_messages
from pm_weekly_report.collectors.progress_collector import load_progress_csv
from pm_weekly_report.config import load_config
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


def test_load_im_messages_and_split():
    start = datetime(2026, 7, 6)
    end = datetime(2026, 7, 12, 23, 59, 59)
    messages = load_im_messages("data/im_messages.json", start, end)
    assert len(messages) == 4
    requirements, risks, others = split_im_messages(messages)
    assert len(requirements) == 1
    assert len(risks) == 2  # 含 #风险 标签 + 投诉关键词自动识别


def test_load_progress_csv():
    rows = load_progress_csv("data/product_progress.csv")
    assert len(rows) == 3
    assert rows[0].product == "产品A"


def test_build_report_with_sample_data():
    config = load_config("config.example.yaml")
    data = build_report(config, reference=datetime(2026, 7, 10))
    assert data.week_label
    assert len(data.progress) == 3
    assert len(data.requirements) >= 1
    assert len(data.risks) >= 1


def test_render_markdown_contains_sections():
    config = load_config("config.example.yaml")
    data = build_report(config, reference=datetime(2026, 7, 10))
    md = render_markdown(data, "核心产品线")
    assert "## 一、本周重要邮件" in md
    assert "## 二、群消息：需求与风险" in md
    assert "## 三、各产品进展" in md
    assert "## 四、待跟进事项" in md
    assert "产品A" in md


def test_extract_action_items():
    start = datetime(2026, 7, 6)
    end = datetime(2026, 7, 12, 23, 59, 59)
    messages = load_im_messages("data/im_messages.json", start, end)
    items = extract_action_items([], messages)
    assert any("定价页" in i.text for i in items)
