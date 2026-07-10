#!/usr/bin/env python3
"""企业微信 / 钉钉机器人 Webhook 接收服务，将群消息写入 data/im_messages.json。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from pm_weekly_report.config import load_config


def _load_messages(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _save_message(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    messages = _load_messages(path)
    fingerprint = f"{entry.get('platform')}|{entry.get('content')}|{entry.get('timestamp')}"
    if any(
        f"{m.get('platform')}|{m.get('content')}|{m.get('timestamp')}" == fingerprint
        for m in messages
    ):
        return
    messages.append(entry)
    with path.open("w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def _parse_simple(payload: dict[str, Any], platform: str) -> dict[str, Any] | None:
    content = (
        payload.get("content")
        or payload.get("text")
        or payload.get("msg", "")
    )
    if isinstance(content, dict):
        content = content.get("content", "")
    content = str(content).strip()
    if not content:
        return None
    return {
        "platform": platform,
        "group": payload.get("group", f"{platform}-group"),
        "sender": payload.get("sender", payload.get("senderNick", "unknown")),
        "content": content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _parse_wecom(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("msgtype") == "text":
        text = payload.get("text", {}).get("content", "").strip()
        if text:
            return {
                "platform": "wecom",
                "group": payload.get("chatid", "wecom-group"),
                "sender": payload.get("from", {}).get(
                    "alias", payload.get("from", {}).get("name", "unknown")
                ),
                "content": text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    return _parse_simple(payload, "wecom")


def _parse_dingtalk(payload: dict[str, Any]) -> dict[str, Any] | None:
    text = payload.get("text", {}).get("content", "").strip()
    if text:
        return {
            "platform": "dingtalk",
            "group": payload.get("conversationTitle", "dingtalk-group"),
            "sender": payload.get("senderNick", "unknown"),
            "content": text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    return _parse_simple(payload, "dingtalk")


def make_handler(messages_file: Path, default_platform: str) -> type[BaseHTTPRequestHandler]:
    class WebhookHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return

            query = parse_qs(self.path.split("?", 1)[-1]) if "?" in self.path else {}
            platform = query.get("platform", [default_platform])[0]

            if platform == "wecom":
                entry = _parse_wecom(payload)
            elif platform == "dingtalk":
                entry = _parse_dingtalk(payload)
            else:
                entry = _parse_wecom(payload) or _parse_dingtalk(payload)

            if entry:
                _save_message(messages_file, entry)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return WebhookHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="IM 消息 Webhook 接收服务")
    parser.add_argument("-c", "--config", default="config.yaml")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--platform", choices=["auto", "wecom", "dingtalk"], default="auto")
    args = parser.parse_args()

    config = load_config(args.config)
    messages_file = Path(config.get("im", {}).get("messages_file", "data/im_messages.json"))
    handler = make_handler(messages_file, args.platform)
    server = HTTPServer((args.host, args.port), handler)
    print(f"Webhook 服务已启动: http://{args.host}:{args.port}/webhook?platform={args.platform}")
    print(f"消息写入: {messages_file}")
    server.serve_forever()


if __name__ == "__main__":
    main()
