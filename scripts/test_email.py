#!/usr/bin/env python3
"""测试邮箱 IMAP 连接（在办公网/VPN 内运行）。"""

from __future__ import annotations

import argparse
import imaplib
import os
import sys

from dotenv import load_dotenv

from pm_weekly_report.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="测试 IMAP 邮箱连接")
    parser.add_argument("-c", "--config", default="config.o-netcom.yaml")
    args = parser.parse_args()

    load_dotenv()
    config = load_config(args.config)
    email_cfg = config.get("email", {})

    host = email_cfg["imap_host"]
    port = int(email_cfg.get("imap_port", 993))
    use_ssl = bool(email_cfg.get("use_ssl", True))
    username = email_cfg.get("username") or os.getenv("EMAIL_USER", "")
    password = email_cfg.get("password") or os.getenv("EMAIL_PASSWORD", "")

    if not username:
        print("错误：请在 .env 中设置 EMAIL_USER=zhengwei@o-netcom.com")
        sys.exit(1)
    if not password:
        print("错误：请在 .env 中设置 EMAIL_PASSWORD（Foxmail 登录密码）")
        print("提示：复制 .env.o-netcom.example 为 .env 后编辑")
        sys.exit(1)

    print(f"连接 {host}:{port} (SSL={use_ssl}) ...")
    try:
        if use_ssl:
            client = imaplib.IMAP4_SSL(host, port, timeout=15)
        else:
            client = imaplib.IMAP4(host, port, timeout=15)
        client.login(username, password)
        status, count = client.select("INBOX")
        print(f"登录成功：{username}")
        print(f"收件箱状态：{status}，邮件数：{count[0].decode()}")
        client.logout()
    except Exception as exc:
        print(f"连接失败：{exc}")
        print("\n提示：mail3.o-netcom.com 通常只能在公司内网或 VPN 下访问。")
        sys.exit(1)


if __name__ == "__main__":
    main()
