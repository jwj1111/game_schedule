"""
数据查询路由。

接口：
  GET /api/news          全量 / 按游戏 / 按时间范围 / 关键词筛选（支持分页）
  GET /api/news/{id}     单条详情
  GET /api/games         所有游戏名列表（前端筛选下拉框用）
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import GameNews
from backend.app.schemas import GamesListResponse, NewsItem, NewsListResponse

router = APIRouter(prefix="/api", tags=["news"])


@router.get("/news", response_model=NewsListResponse)
def list_news(
    game: Optional[str] = Query(None, description="按游戏名筛选"),
    keyword: Optional[str] = Query(None, description="标题关键词搜索"),
    start: Optional[date] = Query(None, description="上线日期起始（含）"),
    end: Optional[date] = Query(None, description="上线日期截止（含）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
):
    """全量 / 多条件筛选查询，按 online_date 降序，支持分页。"""
    query = db.query(GameNews)

    if game:
        query = query.filter(GameNews.game == game)
    if keyword:
        query = query.filter(GameNews.info.contains(keyword))
    if start:
        query = query.filter(GameNews.online_date >= start)
    if end:
        query = query.filter(GameNews.online_date <= end)

    total = query.count()
    items = (
        query
        .order_by(GameNews.online_date.desc(), GameNews.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return NewsListResponse(total=total, items=items)


@router.get("/news/{news_id}", response_model=NewsItem)
def get_news_detail(news_id: int, db: Session = Depends(get_db)):
    """单条详情查询。"""
    record = db.query(GameNews).filter(GameNews.id == news_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@router.get("/games", response_model=GamesListResponse)
def list_games(db: Session = Depends(get_db)):
    """返回当前数据库中所有游戏名（去重，按名称排序）。"""
    rows = (
        db.query(GameNews.game)
        .distinct()
        .order_by(GameNews.game)
        .all()
    )
    return GamesListResponse(games=[r[0] for r in rows])
