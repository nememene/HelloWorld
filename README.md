# 产品线周报生成器

汇总 **邮箱**、**企业微信/钉钉群消息**、**产品进展表**，每周五输出 Markdown 周报。

## 快速开始

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
python -m pm_weekly_report --dry-run
```

生成文件：

```bash
python -m pm_weekly_report
# 输出: reports/weekly_report_YYYY-MM-DD.md
```

## 数据源

| 板块 | 配置 |
|------|------|
| 邮箱 | `config.yaml` → `email.enabled: true`，填写 IMAP |
| 群消息 | `data/im_messages.json`，或由 Webhook 服务写入 |
| 产品进展 | `data/product_progress.csv` 或 Jira |

## 群消息标签

在企微/钉钉群里发：

```
#需求 [产品A] 客户希望支持导出
#风险 [产品B] 第三方 API 延期
#待办 更新定价页 @小王 2026-07-15
```

## Webhook 接收服务

```bash
python -m pm_weekly_report.webhook_server --port 8787
# 回调地址: http://your-host:8787/webhook?platform=wecom
```

## 测试

```bash
python -m pytest tests/ -q
```

详细需求见 [REQUIREMENTS.md](REQUIREMENTS.md)。
