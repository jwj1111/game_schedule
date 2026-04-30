"""
全局应用配置：读 .env，实现本地 SQLite / 线上 MySQL 双环境自动切换。

规范要求：
  - 本地不创建 .env，config 须有合理默认值可直接跑
  - 禁止硬编码密码、密钥、接口地址
"""

from __future__ import annotations

import os
from pathlib import Path
import secrets

from dotenv import load_dotenv

# 项目根目录（backend/app/config.py → 上两级）
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 尝试加载 .env（不存在也不报错，本地默认值兜底）
load_dotenv(PROJECT_ROOT / ".env")

# ---------- 运行环境 ----------
ENV: str = os.getenv("ENV", "local")

# ---------- 数据库连接 ----------
if ENV == "prod":
    _host = os.getenv("MYSQL_HOST", "localhost")
    _port = os.getenv("MYSQL_PORT", "3306")
    _user = os.getenv("MYSQL_USER", "root")
    _pwd = os.getenv("MYSQL_PASSWORD", "")
    _db = os.getenv("MYSQL_DB", "game_schedule")
    DATABASE_URL = f"mysql+pymysql://{_user}:{_pwd}@{_host}:{_port}/{_db}?charset=utf8mb4"
else:
    _sqlite_path = os.getenv("SQLITE_PATH", "./data/game_schedule.db")
    # 相对路径基于项目根
    _abs_path = (PROJECT_ROOT / _sqlite_path).resolve()
    _abs_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{_abs_path}"

# ---------- 数据保留 ----------
DATA_RETENTION_DAYS: int = int(os.getenv("DATA_RETENTION_DAYS", "60"))

# ---------- 清理时间 ----------
CLEANUP_DAY: str = os.getenv("CLEANUP_DAY", "mon")
CLEANUP_HOUR: int = int(os.getenv("CLEANUP_HOUR", "3"))

# ---------- 企微推送 ----------
WECOM_WEBHOOK: str = os.getenv("WECOM_WEBHOOK", "")

# ---------- 管理员认证 ----------
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
AUTH_SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY", "") or secrets.token_urlsafe(32)
AUTH_TOKEN_EXPIRE_SECONDS: int = int(os.getenv("AUTH_TOKEN_EXPIRE_SECONDS", str(7 * 24 * 60 * 60)))


if __name__ == "__main__":
    print(f"ENV            = {ENV}")
    print(f"DATABASE_URL   = {DATABASE_URL}")
    print(f"RETENTION_DAYS = {DATA_RETENTION_DAYS}")
    print(f"WECOM_WEBHOOK  = {WECOM_WEBHOOK[:30]}..." if WECOM_WEBHOOK else "WECOM_WEBHOOK  = (empty)")
