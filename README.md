# 产品线周报生成器

汇总 **邮箱**、**企业微信/钉钉群消息**、**产品进展表**，每周五输出 Markdown 周报（不含 Zoom）。

## 快速开始

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
cp .env.example .env   # 填写邮箱与 Webhook

# 预览（使用 sample 数据）
python3 -m pm_weekly_report --dry-run

# 生成 reports/weekly_report_YYYY-MM-DD.md
python3 -m pm_weekly_report

# 指定第 28 周
python3 -m pm_weekly_report --week 28 --year 2026 --dry-run
```

或使用脚本：

```bash
chmod +x scripts/run_weekly.sh
./scripts/run_weekly.sh --dry-run
```

## 数据源

| 板块 | 来源 | 说明 |
|------|------|------|
| 本周重要邮件 | IMAP 邮箱 | 未配置时自动读 `data/sample_emails.json` |
| 需求/风险/决策 | 企微/钉钉 | `data/im_messages.json` 或 Webhook 写入 |
| 各产品进展 | CSV | `data/product_progress.csv` |

## 群消息标签

```
#需求 [产品A] 客户希望支持导出
#风险 [产品B] 第三方 API 延期
#决策 [产品A] Q3 主推权限重构
#待办 更新定价页 @小王 2026-07-15
```

## Webhook 接收服务

```bash
python3 -m pm_weekly_report.webhook_server --port 8787
```

回调地址：

- 企业微信：`http://your-host:8787/webhook?platform=wecom`
- 钉钉：`http://your-host:8787/webhook?platform=dingtalk`

也支持简单 JSON：`{"content": "#需求 ...", "sender": "小王", "group": "产品A群"}`

## 定时任务（每周五 17:00）

```cron
0 17 * * 5 cd /path/to/project && ./scripts/run_weekly.sh --notify
```

## 昂纳科技邮箱（o-netcom.com）

Foxmail 是客户端，实际邮箱域名为 `@o-netcom.com`。已提供专用配置：

```bash
cp .env.o-netcom.example .env
# 编辑 .env，填入 EMAIL_PASSWORD（邮箱登录密码）

# 测试连接（需在公司内网或 VPN）
python3 scripts/test_email.py -c config.o-netcom.yaml

# 生成周报
python3 -m pm_weekly_report -c config.o-netcom.yaml --dry-run
python3 -m pm_weekly_report -c config.o-netcom.yaml
```

| 项目 | 值 |
|------|-----|
| 收件服务器 | `mail3.o-netcom.com` |
| IMAP 端口 | `5000` |
| SSL | 关闭 |
| 用户名 | `zhengwei@o-netcom.com` |
| 密码 | 邮箱登录密码（与 Foxmail 相同） |

## 测试

```bash
python3 -m pytest tests/ -q
```

完整需求见 [REQUIREMENTS.md](REQUIREMENTS.md)。
