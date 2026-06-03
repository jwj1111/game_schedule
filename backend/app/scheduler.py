"""
APScheduler 定时任务管理。

注册两个定时任务：
  1. 定时爬取 + 预处理 + 入库（默认间隔由 sites.yaml 控制，可由 .env 的 SPIDER_INTERVAL 覆盖）
  2. 定期过期清理（时间由 .env 的 CLEANUP_DAY + CLEANUP_HOUR 控制）
"""

from __future__ import annotations

import time as _time
from collections import deque
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.config import CLEANUP_DAY, CLEANUP_HOUR, DATA_RETENTION_DAYS
from backend.app.config import PUSH_TIMES, SPIDER_START_TIME, WECOM_WEBHOOK
from backend.app.crud import cleanup_expired
from backend.app.database import SessionLocal
from backend.app.pipeline import run_pipeline
from backend.spiders.config import format_duration, load_sites_config

_scheduler: BackgroundScheduler | None = None

# 最近执行记录（最多 20 条，新的在前）
recent_runs: deque[dict] = deque(maxlen=20)


def _compute_start_date(hhmm: str) -> datetime | None:
    """解析 SPIDER_START_TIME（HH:MM）为今天对应时刻的 datetime。

    用作 APScheduler interval trigger 的锚点（在过去也无所谓，
    APScheduler 会自动按 anchor + N×interval 计算大于 now 的下一次执行时刻）。

    格式异常返回 None，等价于不设锚点（沿用旧行为：启动即开始计时）。
    """
    if not hhmm:
        return None
    try:
        h, m = map(int, hhmm.split(":"))
        return datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
    except (ValueError, TypeError):
        return None


def _record_run(job: str, status: str, duration: float, detail: str):
    """记录一次任务执行结果。"""
    recent_runs.appendleft({
        "job": job,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "duration": round(duration, 1),
        "detail": detail,
    })


def _crawl_and_save():
    """定时任务回调：完整流水线。"""
    print("\n[定时任务] 开始爬取...")
    start = _time.time()
    try:
        run_pipeline()
        duration = _time.time() - start
        _record_run("crawl", "success", duration, f"爬取入库完成，耗时 {duration:.1f}s")
        print("[定时任务] 爬取入库完成")
    except Exception as e:
        duration = _time.time() - start
        _record_run("crawl", "failed", duration, str(e)[:200])
        print(f"[定时任务] 爬取失败: {e}")


def _cleanup():
    """定时任务回调：过期清理。"""
    print("\n[定时任务] 开始过期清理...")
    start = _time.time()
    db = SessionLocal()
    try:
        cleanup_expired(db, DATA_RETENTION_DAYS)
        duration = _time.time() - start
        _record_run("cleanup", "success", duration, f"过期清理完成，耗时 {duration:.1f}s")
    except Exception as e:
        duration = _time.time() - start
        _record_run("cleanup", "failed", duration, str(e)[:200])
        print(f"[定时任务] 清理失败: {e}")
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

    # 解析锚点：留空或格式非法都回退为 None（即旧行为）
    crawl_start_date = _compute_start_date(SPIDER_START_TIME)
    if SPIDER_START_TIME and crawl_start_date is None:
        print(f"[调度器] 警告：SPIDER_START_TIME='{SPIDER_START_TIME}' 格式无效（应为 HH:MM），已忽略")

    # 任务 1：定时爬取（默认间隔由 sites.yaml 控制，可由 .env 的 SPIDER_INTERVAL 覆盖）
    _scheduler.add_job(
        _crawl_and_save,
        trigger="interval",
        seconds=interval_sec,
        start_date=crawl_start_date,
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

    # 任务 3：企微定时推送（PUSH_TIMES 为空或 WECOM_WEBHOOK 为空时跳过）
    push_schedule_desc = ""
    if WECOM_WEBHOOK and PUSH_TIMES:
        from backend.app.notifier import push_notify

        def _push_with_record():
            """推送回调：带执行记录。"""
            start = _time.time()
            try:
                push_notify()
                duration = _time.time() - start
                _record_run("push", "success", duration, f"推送完成，耗时 {duration:.1f}s")
            except Exception as e:
                duration = _time.time() - start
                _record_run("push", "failed", duration, str(e)[:200])

        time_parts = [t.strip() for t in PUSH_TIMES.split(",") if t.strip()]
        for i, t in enumerate(time_parts):
            parts = t.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            _scheduler.add_job(
                _push_with_record,
                trigger="cron",
                hour=hour,
                minute=minute,
                id=f"push_job_{i}",
                name=f"企微推送（每天 {hour}:{minute:02d}）",
                max_instances=1,
            )
        push_schedule_desc = f"，推送={PUSH_TIMES}"

    _scheduler.start()
    anchor_desc = f"，锚点={SPIDER_START_TIME}" if crawl_start_date else ""
    print(f"[调度器] 已启动：爬取间隔={format_duration(interval_sec)}{anchor_desc}，"
          f"清理=每周{CLEANUP_DAY} {CLEANUP_HOUR}:00{push_schedule_desc}")


def shutdown_scheduler():
    """关闭调度器（用于 FastAPI shutdown 事件）。"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("[调度器] 已关闭")


def get_scheduler_info() -> dict:
    """获取调度器运行状态（供 API 层调用）。"""
    info = {"running": False, "jobs": [], "recent_runs": list(recent_runs)}
    if _scheduler and _scheduler.running:
        info["running"] = True
        for job in _scheduler.get_jobs():
            next_run_str = None
            if job.next_run_time:
                next_run_str = job.next_run_time.strftime("%Y-%m-%d %H:%M")
            info["jobs"].append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run_str,
            })
    return info
