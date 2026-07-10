from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import requests

from pm_weekly_report.collectors.email_collector import fetch_emails
from pm_weekly_report.collectors.im_collector import load_im_messages, split_im_messages
from pm_weekly_report.collectors.progress_collector import fetch_jira_progress, load_progress_csv
from pm_weekly_report.config import load_config
from pm_weekly_report.models import WeeklyReportData
from pm_weekly_report.outputs.markdown_report import render_markdown
from pm_weekly_report.processors.action_extractor import extract_action_items, get_week_range


def build_report(config: dict, reference: datetime | None = None) -> WeeklyReportData:
    week_start, week_end, week_label, date_range = get_week_range(reference)

    emails = fetch_emails(config, week_start, week_end)

    im_messages: list = []
    if config.get("im", {}).get("enabled", True):
        im_file = config.get("im", {}).get("messages_file", "data/im_messages.json")
        im_messages = load_im_messages(im_file, week_start, week_end)

    requirements, risks, others = split_im_messages(im_messages)

    progress = []
    if config.get("progress", {}).get("enabled", True):
        csv_file = config.get("progress", {}).get("csv_file", "data/product_progress.csv")
        progress = load_progress_csv(csv_file)
        if not progress:
            progress = fetch_jira_progress(config)

    action_items = extract_action_items(emails, im_messages)

    return WeeklyReportData(
        week_label=week_label,
        date_range=date_range,
        emails=emails,
        requirements=requirements,
        risks=risks,
        other_im_messages=others,
        progress=progress,
        action_items=action_items,
    )


def save_report(markdown: str, output_dir: str, reference: datetime | None = None) -> Path:
    ref = reference or datetime.now()
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"weekly_report_{ref.strftime('%Y-%m-%d')}.md"
    path = out_dir / filename
    path.write_text(markdown, encoding="utf-8")
    return path


def notify_wecom(webhook: str, markdown: str) -> None:
    if not webhook:
        return
    summary = "\n".join(markdown.splitlines()[:20])
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": summary + "\n\n> 完整周报已生成，请查看本地 reports 目录。"},
    }
    requests.post(webhook, json=payload, timeout=15)


def main() -> None:
    parser = argparse.ArgumentParser(description="产品线周报生成器（邮箱 + 企微/钉钉 + 产品进展）")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅打印 Markdown，不写文件")
    parser.add_argument("--date", help="指定参考日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--notify", action="store_true", help="生成后推送企微摘要")
    args = parser.parse_args()

    config = load_config(args.config)
    reference = datetime.strptime(args.date, "%Y-%m-%d") if args.date else None

    data = build_report(config, reference)
    product_line = config.get("report", {}).get("product_line_name", "产品线")
    markdown = render_markdown(data, product_line)

    if args.dry_run:
        print(markdown)
        return

    output_dir = config.get("report", {}).get("output_dir", "reports")
    path = save_report(markdown, output_dir, reference or datetime.now())
    print(f"周报已生成: {path}")

    notify_cfg = config.get("notify", {})
    if args.notify or notify_cfg.get("enabled"):
        notify_wecom(notify_cfg.get("wecom_webhook", ""), markdown)


if __name__ == "__main__":
    main()
