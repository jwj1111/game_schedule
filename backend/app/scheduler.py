"""
APScheduler 定时任务管理。

注册两个定时任务：
  1. 定时爬取 + 预处理 + 入库（间隔由 sites.yaml 的 interval 控制）
  2. 定时过期清理（每周一次）
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.config import CLEANUP_DAY, CLEANUP_HOUR, DATA_RETENTION_DAYS
from backend.app.crud import bulk_insert_new, cleanup_expired
from backend.app.database import SessionLocal
from backend.app.preprocessor import preprocess
from backend.spiders.config import format_duration, load_sites_config
from backend.spiders.runner import crawl_all

_scheduler: BackgroundScheduler | None = None


def _crawl_and_save():
    """定时任务回调：爬取 → 预处理 → 入库。"""
    print("\n[定时任务] 开始爬取...")
    raw_items = crawl_all()
    if not raw_items:
        print("[定时任务] 无数据，跳过入库")
        return

    filtered = preprocess(raw_items)
    if not filtered:
        print("[定时任务] 预处理后无有效数据，跳过入库")
        return

    db = SessionLocal()
    try:
        bulk_insert_new(db, filtered)
    finally:
        db.close()
    print("[定时任务] 爬取入库完成")


def _cleanup():
    """定时任务回调：过期清理。"""
    print("\n[定时任务] 开始过期清理...")
    db = SessionLocal()
    try:
        cleanup_expired(db, DATA_RETENTION_DAYS)
    finally:
        db.close()


def start_scheduler():
    """启动 APScheduler，注册定时任务。"""
    global _scheduler
    if _scheduler is not None:
        return

    cfg = load_sites_config()
    interval_sec = cfg.schedule.interval_seconds

    _scheduler = BackgroundScheduler()

    # 任务 1：定时爬取（间隔由 sites.yaml 控制）
    _scheduler.add_job(
        _crawl_and_save,
        trigger="interval",
        seconds=interval_sec,
        id="crawl_job",
        name=f"定时爬取（每 {format_duration(interval_sec)}）",
        max_instances=1,
    )

    # 任务 2：定期清理过期数据（时间由 .env 配置）
    _scheduler.add_job(
        _cleanup,
        trigger="cron",
        day_of_week=CLEANUP_DAY,
        hour=CLEANUP_HOUR,
        minute=0,
        id="cleanup_job",
        name=f"定期过期清理（每周{CLEANUP_DAY} {CLEANUP_HOUR}:00）",
        max_instances=1,
    )

    _scheduler.start()
    print(f"[调度器] 已启动：爬取间隔={format_duration(interval_sec)}，"
          f"清理=每周{CLEANUP_DAY} {CLEANUP_HOUR}:00")


def shutdown_scheduler():
    """关闭调度器（用于 FastAPI shutdown 事件）。"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("[调度器] 已关闭")
