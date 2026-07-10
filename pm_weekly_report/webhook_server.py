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


MESSAGES_FILE = Path("data/im_messages.json")


def _load_messages() -> list[dict[str, Any]]:
    if not MESSAGES_FILE.exists():
        return []
    with MESSAGES_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _save_message(entry: dict[str, Any]) -> None:
    MESSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    messages = _load_messages()
    messages.append(entry)
    with MESSAGES_FILE.open("w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def _parse_wecom(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("msgtype") != "text":
        return None
    text = payload.get("text", {}).get("content", "").strip()
    if not text:
        return None
    return {
        "platform": "wecom",
        "group": payload.get("chatid", "wecom-group"),
        "sender": payload.get("from", {}).get("alias", payload.get("from", {}).get("name", "unknown")),
        "content": text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _parse_dingtalk(payload: dict[str, Any]) -> dict[str, Any] | None:
    text = payload.get("text", {}).get("content", "").strip()
    if not text:
        return None
    return {
        "platform": "dingtalk",
        "group": payload.get("conversationTitle", "dingtalk-group"),
        "sender": payload.get("senderNick", "unknown"),
        "content": text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


class WebhookHandler(BaseHTTPRequestHandler):
    platform = "auto"

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
        platform = query.get("platform", [self.platform])[0]

        if platform == "wecom":
            entry = _parse_wecom(payload)
        elif platform == "dingtalk":
            entry = _parse_dingtalk(payload)
        else:
            entry = _parse_wecom(payload) or _parse_dingtalk(payload)

        if entry:
            _save_message(entry)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="IM 消息 Webhook 接收服务")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--platform", choices=["auto", "wecom", "dingtalk"], default="auto")
    args = parser.parse_args()

    WebhookHandler.platform = args.platform
    server = HTTPServer((args.host, args.port), WebhookHandler)
    print(f"Webhook 服务已启动: http://{args.host}:{args.port}/webhook?platform={args.platform}")
    server.serve_forever()


if __name__ == "__main__":
    main()
