"""
数据查询路由。

接口：
  GET /api/calendar    统一查询（合并爬虫+标注+事件，按月日历加载）
  GET /api/games       所有游戏名列表
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import union_all
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import GameNews, GameOwner, UserAnnotation, UserEvent
from backend.app.schemas import CalendarItem, CalendarResponse, GamesListResponse

router = APIRouter(prefix="/api", tags=["query"])


@router.get("/calendar", response_model=CalendarResponse)
def calendar_query(
    start_date: date = Query(..., description="起始日期（含）"),
    end_date: date = Query(..., description="截止日期（含）"),
    games: Optional[str] = Query(None, description="游戏名，多个逗号分隔"),
    keyword: Optional[str] = Query(None, description="标题关键词搜索"),
    db: Session = Depends(get_db),
):
    """
    统一日历查询：合并爬虫数据 + 用户事件，附带标注和负责人信息。
    排序：日期升序 + 优先级降序。
    隐藏的爬虫数据不返回。
    """
    game_list = [g.strip() for g in games.split(",") if g.strip()] if games else []

    # 预加载所有负责人映射（数据量小，一次查完）
    owner_map = {o.game: o.owners for o in db.query(GameOwner).all()}

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
        # 跳过被隐藏的
        if ann and ann.hidden:
            continue

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
            hidden=False,
            owners=owner_map.get(news.game, []),
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
        ))

    # 排序：日期升序 + 优先级降序
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
