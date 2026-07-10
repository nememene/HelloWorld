from __future__ import annotations

import csv
from pathlib import Path

from pm_weekly_report.models import ProductProgress


def load_progress_csv(csv_file: str | Path) -> list[ProductProgress]:
    path = Path(csv_file)
    if not path.exists():
        return []

    rows: list[ProductProgress] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                ProductProgress(
                    product=row.get("product", "").strip(),
                    completed=row.get("completed", "").strip(),
                    next_plan=row.get("next_plan", "").strip(),
                    status=row.get("status", "").strip(),
                    risk=row.get("risk", "").strip(),
                    owner=row.get("owner", "").strip(),
                )
            )
    return rows


def fetch_jira_progress(config: dict) -> list[ProductProgress]:
    jira_cfg = config.get("progress", {}).get("jira", {})
    if not jira_cfg.get("enabled"):
        return []

    base_url = jira_cfg.get("base_url", "").rstrip("/")
    email = jira_cfg.get("email", "")
    api_token = jira_cfg.get("api_token", "")
    project_keys = jira_cfg.get("project_keys", [])

    if not base_url or not email or not api_token or not project_keys:
        return []

    try:
        import requests
    except ImportError:
        return []

    rows: list[ProductProgress] = []
    auth = (email, api_token)
    headers = {"Accept": "application/json"}

    for key in project_keys:
        jql = (
            f'project = "{key}" AND updated >= -7d '
            f'ORDER BY updated DESC'
        )
        resp = requests.get(
            f"{base_url}/rest/api/2/search",
            params={"jql": jql, "maxResults": 20, "fields": "summary,status,assignee"},
            auth=auth,
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            continue

        issues = resp.json().get("issues", [])
        done = [i["fields"]["summary"] for i in issues if i["fields"]["status"]["name"] in {"Done", "完成", "Closed"}]
        in_progress = [
            i["fields"]["summary"]
            for i in issues
            if i["fields"]["status"]["name"] not in {"Done", "完成", "Closed"}
        ]

        rows.append(
            ProductProgress(
                product=key,
                completed="；".join(done[:5]) if done else "—",
                next_plan="；".join(in_progress[:5]) if in_progress else "—",
                status="正常" if in_progress else "收尾",
                risk="",
                owner="",
            )
        )

    return rows
