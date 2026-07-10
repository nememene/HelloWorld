#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  echo "已创建 config.yaml，请填写邮箱和 Webhook 配置"
fi

python3 -m pm_weekly_report "$@"
