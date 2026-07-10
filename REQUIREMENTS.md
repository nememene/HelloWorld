# 产品线周报生成器 — 需求说明（无 Zoom 版）

## 1. 目标

每周五自动生成产品线周报 Markdown，汇总邮箱、企业微信/钉钉群消息、各产品进展，供粘贴到邮件、企微文档或钉钉日志。

## 2. 输入源

| 板块 | 数据来源 | 采集方式 |
|------|----------|----------|
| 本周重要邮件 | 邮箱 | IMAP 拉取（支持 Outlook/腾讯企业邮等） |
| 群里的需求/风险 | 企业微信 / 钉钉 | 机器人 Webhook 写入本地 JSON，或读取历史消息文件 |
| 各产品进展 | 表格 / Jira | CSV/Excel 维护表，或 Jira REST API（可选） |

**不包含：** Zoom 会议转写、会议纪要自动提取。

## 3. 输出

- 格式：**Markdown（.md）**
- 默认路径：`reports/weekly_report_YYYY-MM-DD.md`
- 可选：通过企业微信 / 钉钉 Webhook 推送摘要

### 3.1 报告结构

```markdown
# 产品线周报 · {年份} 第 {周} 周（{起止日期}）

## 一、本周重要邮件
- [产品A] 主题摘要 — 发件人 · 日期 · 分类标签

## 二、群消息：需求与风险
### 需求
- ...

### 风险
- ...

## 三、各产品进展
| 产品 | 本周完成 | 下周计划 | 状态 | 风险 |
|------|----------|----------|------|------|

## 四、待跟进事项
- [ ] 事项 — 负责人 — 截止日期

## 五、备注
（可选，手动补充）
```

## 4. 功能需求

### 4.1 邮箱采集

- 通过 IMAP 连接邮箱，拉取本周内邮件
- 支持按发件人域名、主题关键词、标签过滤
- 自动分类：`需求反馈` / `风险` / `待决策` / `FYI` / `待回复`
- 去重：同一 `Message-ID` 不重复入库

### 4.2 IM 消息采集

- 企业微信 / 钉钉机器人回调写入 `data/im_messages.json`
- 支持标签解析：`#需求` `#风险` `#决策` `#待办 @人 日期`
- 无标签时按关键词规则分类

### 4.3 产品进展

- 读取 `data/product_progress.csv`（或配置路径）
- 列：`product, completed, next_plan, status, risk, owner`
- 可选 Jira：按项目 key 拉取本周 Done / In Progress

### 4.4 报告生成

- 合并三类数据，生成 Markdown
- 从群消息和邮件中提取待办（含 `@` 与日期）
- 支持 `--week` 指定周次，`--dry-run` 仅打印不落盘

## 5. 非功能需求

- Python 3.10+
- 配置外置：`config.yaml`（邮箱、过滤规则、路径）
- 密钥不入库：环境变量或 `.env`
- 无 AI 也可运行（规则分类）；可选 OpenAI 增强摘要

## 6. 配置项

```yaml
report:
  product_line_name: "核心产品线"
  output_dir: reports

email:
  enabled: true
  imap_host: imap.example.com
  imap_port: 993
  username: ${EMAIL_USER}
  password: ${EMAIL_PASSWORD}
  since_days: 7
  filters:
    domains: ["customer.com", "partner.com"]
    subject_keywords: ["需求", "bug", "上线", "合同"]
    exclude_subject: ["订阅", "广告"]

im:
  enabled: true
  messages_file: data/im_messages.json
  platforms: ["wecom", "dingtalk"]

progress:
  enabled: true
  csv_file: data/product_progress.csv
  jira:
    enabled: false
    base_url: https://jira.example.com
    project_keys: ["PROD-A", "PROD-B"]

notify:
  enabled: false
  wecom_webhook: ${WECOM_WEBHOOK}
```

## 7. 验收标准

- [ ] `python -m pm_weekly_report` 可生成周报 Markdown
- [ ] 无邮箱配置时，可用 sample 数据跑通
- [ ] 群消息 `#需求` / `#风险` 正确分栏
- [ ] 产品进展表正确渲染为 Markdown 表格
- [ ] 输出可直接粘贴到邮件 / 企微 / 钉钉
