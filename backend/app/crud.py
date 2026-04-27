"""
数据库读写操作。

提供:
  - bulk_insert_new(): 去重入库（game + info 联合判断）
  - cleanup_expired(): 按 online_date 过期天数清理（带 WHERE，合规）
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.app.models import GameNews


def bulk_insert_new(db: Session, items: List[Dict[str, Any]]) -> int:
    """
    批量去重入库。

    去重规则：game + info 联合唯一。
    已存在的跳过，不存在的插入。

    Args:
        db: 数据库会话
        items: 预处理后的数据 [{"game", "info", "link", "online_date"}, ...]

    Returns:
        本次实际新增的条数
    """
    if not items:
        return 0

    inserted = 0
    for item in items:
        # 检查是否已存在
        exists = db.query(GameNews.id).filter(
            and_(
                GameNews.game == item["game"],
                GameNews.info == item["info"],
            )
        ).first()

        if exists:
            continue

        record = GameNews(
            game=item["game"],
            info=item["info"],
            link=item["link"],
            online_date=item["online_date"],
        )
        db.add(record)
        inserted += 1

    if inserted > 0:
        db.commit()

    print(f"入库完成：输入 {len(items)} 条，新增 {inserted} 条，跳过 {len(items) - inserted} 条（已存在）")
    return inserted


def cleanup_expired(db: Session, retention_days: int) -> int:
    """
    清理过期数据：online_date < 今天 - retention_days 的记录直接删除。

    Args:
        db: 数据库会话
        retention_days: 保留天数，0 表示永不删除

    Returns:
        本次删除的条数
    """
    if retention_days <= 0:
        print("数据保留策略：永不删除，跳过清理")
        return 0

    cutoff = date.today() - timedelta(days=retention_days)
    count = db.query(GameNews).filter(GameNews.online_date < cutoff).delete()
    db.commit()

    print(f"过期清理完成：删除 online_date < {cutoff} 的记录 {count} 条")
    return count
