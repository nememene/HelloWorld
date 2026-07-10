#!/usr/bin/env bash
# 在 Git Bash 中运行：bash scripts/run_setup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> 项目目录: $ROOT"

if [[ ! -f config.o-netcom.yaml ]]; then
  echo "错误: 未找到 config.o-netcom.yaml，请先执行:"
  echo "  git checkout cursor/pm-weekly-report-c105"
  exit 1
fi

echo "==> 安装 Python 依赖..."
python -m pip install -r requirements.txt -q

if [[ ! -f .env ]]; then
  cp .env.o-netcom.example .env
  echo "==> 已创建 .env，请填写 EMAIL_PASSWORD"
  notepad .env 2>/dev/null || nano .env || vi .env
fi

# shellcheck disable=SC1091
source .env 2>/dev/null || true
if [[ -z "${EMAIL_PASSWORD:-}" ]]; then
  echo ""
  echo "请在 .env 中设置 EMAIL_PASSWORD 后重新运行本脚本"
  exit 1
fi

echo "==> 测试邮箱连接 mail3.o-netcom.com:5000 ..."
PYTHONPATH="$ROOT" python scripts/test_email.py -c config.o-netcom.yaml

echo ""
echo "==> 生成周报预览..."
PYTHONPATH="$ROOT" python -m pm_weekly_report -c config.o-netcom.yaml --dry-run

echo ""
echo "==> 写入周报文件..."
PYTHONPATH="$ROOT" python -m pm_weekly_report -c config.o-netcom.yaml
echo "完成！请查看 reports/ 目录"
