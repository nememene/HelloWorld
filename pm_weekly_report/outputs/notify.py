from __future__ import annotations

import json

import requests


def notify_wecom(webhook: str, markdown: str) -> bool:
    if not webhook:
        return False
    summary = "\n".join(markdown.splitlines()[:25])
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": summary + "\n\n> 完整周报已生成，请查看 reports 目录。",
        },
    }
    resp = requests.post(webhook, json=payload, timeout=15)
    return resp.status_code == 200


def notify_dingtalk(webhook: str, markdown: str) -> bool:
    if not webhook:
        return False
    summary = "\n".join(markdown.splitlines()[:25])
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "产品线周报",
            "text": summary + "\n\n> 完整周报已生成，请查看 reports 目录。",
        },
    }
    resp = requests.post(
        webhook,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    return resp.status_code == 200
