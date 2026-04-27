"""
Pydantic 响应模型，定义 FastAPI 接口返回给前端的 JSON 结构。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class NewsItem(BaseModel):
    """单条资讯"""
    id: int
    game: str
    info: str
    link: str
    online_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class NewsListResponse(BaseModel):
    """资讯列表响应（带分页信息）"""
    total: int
    items: List[NewsItem]


class GamesListResponse(BaseModel):
    """游戏名称列表响应"""
    games: List[str]
