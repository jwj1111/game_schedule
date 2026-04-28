"""
数据库读写操作。

涵盖：
  - 爬虫数据：批量去重入库 / 过期清理（级联删除标注）
  - 标注：创建或更新 / 查询
  - 自定义事件：增删改查
  - 游戏负责人：增改查
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.app.models import GameNews, GameOwner, UserAnnotation, UserEvent


# ==================== 爬虫数据 ====================

def bulk_insert_new(db: Session, items: List[Dict[str, Any]]) -> int:
    """批量去重入库（game + info 联合唯一）。"""
    if not items:
        return 0

    inserted = 0
    for item in items:
        exists = db.query(GameNews.id).filter(
            and_(GameNews.game == item["game"], GameNews.info == item["info"])
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
    清理过期数据。
    GameNews 删除时，关联的 UserAnnotation 会被 ORM cascade 自动删除。
    """
    if retention_days <= 0:
        print("数据保留策略：永不删除，跳过清理")
        return 0

    cutoff = date.today() - timedelta(days=retention_days)
    # 先查出要删的记录，让 ORM cascade 生效
    expired = db.query(GameNews).filter(GameNews.online_date < cutoff).all()
    count = len(expired)
    for record in expired:
        db.delete(record)
    db.commit()

    print(f"过期清理完成：删除 online_date < {cutoff} 的记录 {count} 条（含关联标注）")
    return count


# ==================== 标注 ====================

def get_annotation(db: Session, news_id: int) -> Optional[UserAnnotation]:
    """获取某条爬虫数据的标注。"""
    return db.query(UserAnnotation).filter(UserAnnotation.news_id == news_id).first()


def upsert_annotation(db: Session, news_id: int, data: Dict[str, Any]) -> UserAnnotation:
    """创建或更新标注（只更新传入的非 None 字段）。"""
    ann = get_annotation(db, news_id)
    if ann is None:
        ann = UserAnnotation(news_id=news_id)
        db.add(ann)

    for field in ("priority", "alias", "resource_ready", "hidden"):
        if field in data and data[field] is not None:
            setattr(ann, field, data[field])

    db.commit()
    db.refresh(ann)
    return ann


# ==================== 自定义事件 ====================

def create_event(db: Session, data: Dict[str, Any]) -> UserEvent:
    """新建自定义事件。"""
    event = UserEvent(**data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_event(db: Session, event_id: int) -> Optional[UserEvent]:
    """获取单条事件。"""
    return db.query(UserEvent).filter(UserEvent.id == event_id).first()


def update_event(db: Session, event_id: int, data: Dict[str, Any]) -> Optional[UserEvent]:
    """更新事件（只更新传入的非 None 字段）。"""
    event = get_event(db, event_id)
    if event is None:
        return None

    for key, val in data.items():
        if val is not None:
            setattr(event, key, val)

    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: int) -> bool:
    """物理删除自定义事件。"""
    event = get_event(db, event_id)
    if event is None:
        return False
    db.delete(event)
    db.commit()
    return True


# ==================== 游戏负责人 ====================

def get_all_owners(db: Session) -> List[GameOwner]:
    """全部游戏负责人。"""
    return db.query(GameOwner).order_by(GameOwner.game).all()


def get_owner_by_game(db: Session, game: str) -> Optional[GameOwner]:
    """按游戏名查询负责人。"""
    return db.query(GameOwner).filter(GameOwner.game == game).first()


def create_owner(db: Session, game: str, owners: List[str]) -> GameOwner:
    """新增游戏负责人。"""
    record = GameOwner(game=game, owners=owners)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_owner(db: Session, game: str, owners: List[str]) -> Optional[GameOwner]:
    """修改负责人列表。"""
    record = get_owner_by_game(db, game)
    if record is None:
        return None
    record.owners = owners
    db.commit()
    db.refresh(record)
    return record
