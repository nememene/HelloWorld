#!/usr/bin/env python3
"""生成周报（Windows 可直接运行: python generate_report.py）"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from pm_weekly_report.__main__ import main

if __name__ == "__main__":
    main()
