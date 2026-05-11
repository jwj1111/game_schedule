"""
数据查询路由。

接口：
  GET /api/calendar    统一查询（合并爬虫+标注+事件，按月日历加载）
  GET /api/games       所有游戏名列表
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.auth import require_admin
from backend.app.database import get_db
from backend.app.models import GameNews, GameOwner, UserAnnotation, UserEvent
from backend.app.schemas import CalendarItem, CalendarResponse, GamesListResponse, HiddenListResponse

router = APIRouter(prefix="/api", tags=["query"])


@router.get("/calendar", response_model=CalendarResponse)
def calendar_query(
    start_date: date = Query(..., description="起始日期（含）"),
    end_date: date = Query(..., description="截止日期（含）"),
    games: Optional[str] = Query(None, description="游戏名，多个逗号分隔"),
    owners: Optional[str] = Query(None, description="负责人，多个逗号分隔"),
    keyword: Optional[str] = Query(None, description="标题关键词搜索"),
    db: Session = Depends(get_db),
):
    """
    统一日历查询：合并爬虫数据 + 用户事件，附带标注和负责人信息。
    排序：日期升序 + 优先级降序。
    支持按游戏 + 按负责人联合筛选。
    """
    game_list = [g.strip() for g in games.split(",") if g.strip()] if games else []
    owner_list = [o.strip() for o in owners.split(",") if o.strip()] if owners else []

    # 预加载所有负责人映射
    owner_map = {o.game: o.owners for o in db.query(GameOwner).all()}

    # 如果按负责人筛选，先找出该负责人对应的游戏
    if owner_list:
        owner_games = [
            game for game, game_owners in owner_map.items()
            if any(o in game_owners for o in owner_list)
        ]
        # 与游戏筛选取并集
        if game_list:
            game_list = list(set(game_list) | set(owner_games))
        else:
            game_list = owner_games
        if not game_list:
            return CalendarResponse(total=0, items=[])

    items: List[CalendarItem] = []

    # ---- 爬虫数据 + 标注 ----
    news_query = db.query(GameNews).filter(
        GameNews.online_date >= start_date,
        GameNews.online_date <= end_date,
    )
    if game_list:
        news_query = news_query.filter(GameNews.game.in_(game_list))
    if keyword:
        news_query = news_query.filter(GameNews.info.contains(keyword))

    for news in news_query.all():
        ann = news.annotation
        is_hidden = bool(ann and ann.hidden)

        items.append(CalendarItem(
            id=news.id,
            source="news",
            game=news.game,
            title=news.info,
            link=news.link,
            item_date=news.online_date,
            priority=ann.priority if ann else 0,
            alias=ann.alias if ann else "",
            resource_ready=ann.resource_ready if ann else False,
            hidden=is_hidden,
            owners=owner_map.get(news.game, []),
            created_at=news.created_at,
        ))

    # ---- 用户事件 ----
    event_query = db.query(UserEvent).filter(
        UserEvent.event_date >= start_date,
        UserEvent.event_date <= end_date,
    )
    if game_list:
        event_query = event_query.filter(UserEvent.game.in_(game_list))
    if keyword:
        event_query = event_query.filter(UserEvent.description.contains(keyword))

    for event in event_query.all():
        items.append(CalendarItem(
            id=event.id,
            source="event",
            game=event.game,
            title=event.description,
            link="",
            item_date=event.event_date,
            priority=event.priority,
            alias=event.alias,
            resource_ready=event.resource_ready,
            hidden=False,
            owners=owner_map.get(event.game, []),
            created_at=event.created_at,
        ))

    # 排序：日期升序 + 优先级降序
    items.sort(key=lambda x: (x.item_date, -x.priority))

    return CalendarResponse(total=len(items), items=items)


@router.get("/overview", response_model=CalendarResponse)
def overview_query(db: Session = Depends(get_db)):
    """资讯速览数据：过去 24 小时入库 + 未来 15 天 + 过去 7 天相关事项。"""
    today = date.today()
    range_start = today - timedelta(days=7)
    range_end = today + timedelta(days=15)
    now = datetime.now()
    created_start = now - timedelta(hours=24)
    created_end = now

    owner_map = {o.game: o.owners for o in db.query(GameOwner).all()}
    items_by_key = {}

    news_rows = db.query(GameNews).filter(or_(
        GameNews.created_at.between(created_start, created_end),
        GameNews.online_date.between(range_start, range_end),
    )).all()
    for news in news_rows:
        ann = news.annotation
        is_hidden = bool(ann and ann.hidden)
        item = CalendarItem(
            id=news.id,
            source="news",
            game=news.game,
            title=news.info,
            link=news.link,
            item_date=news.online_date,
            priority=ann.priority if ann else 0,
            alias=ann.alias if ann else "",
            resource_ready=ann.resource_ready if ann else False,
            hidden=is_hidden,
            owners=owner_map.get(news.game, []),
            created_at=news.created_at,
        )
        items_by_key[(item.source, item.id)] = item

    event_rows = db.query(UserEvent).filter(or_(
        UserEvent.created_at.between(created_start, created_end),
        UserEvent.event_date.between(range_start, range_end),
    )).all()
    for event in event_rows:
        item = CalendarItem(
            id=event.id,
            source="event",
            game=event.game,
            title=event.description,
            link="",
            item_date=event.event_date,
            priority=event.priority,
            alias=event.alias,
            resource_ready=event.resource_ready,
            hidden=False,
            owners=owner_map.get(event.game, []),
            created_at=event.created_at,
        )
        items_by_key[(item.source, item.id)] = item

    items = list(items_by_key.values())
    items.sort(key=lambda x: (x.item_date, -x.priority))
    return CalendarResponse(total=len(items), items=items)


@router.get("/games", response_model=GamesListResponse)
def list_games(db: Session = Depends(get_db)):
    """返回当前所有游戏名（爬虫 + 事件 + 负责人表去重合并）。"""
    news_games = {r[0] for r in db.query(GameNews.game).distinct().all()}
    event_games = {r[0] for r in db.query(UserEvent.game).distinct().all()}
    owner_games = {r[0] for r in db.query(GameOwner.game).distinct().all()}

    all_games = sorted(news_games | event_games | owner_games)
    return GamesListResponse(games=all_games)


@router.get("/owner-names", response_model=dict)
def list_owner_names(db: Session = Depends(get_db)):
    """返回所有负责人姓名（去重，前端筛选下拉框用）。"""
    all_owners = set()
    for record in db.query(GameOwner).all():
        for name in record.owners:
            all_owners.add(name)
    return {"owners": sorted(all_owners)}


@router.get("/hidden", response_model=HiddenListResponse)
def list_hidden(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """返回所有被隐藏的爬虫数据（用于恢复显示）。"""
    rows = (
        db.query(GameNews, UserAnnotation)
        .join(UserAnnotation, GameNews.id == UserAnnotation.news_id)
        .filter(UserAnnotation.hidden == True)
        .order_by(GameNews.online_date.desc())
        .all()
    )
    items = []
    for news, ann in rows:
        items.append(CalendarItem(
            id=news.id,
            source="news",
            game=news.game,
            title=news.info,
            link=news.link,
            item_date=news.online_date,
            priority=ann.priority,
            alias=ann.alias,
            resource_ready=ann.resource_ready,
            hidden=True,
            owners=[],
            created_at=news.created_at,
        ))
    return HiddenListResponse(total=len(items), items=items)
