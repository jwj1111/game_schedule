"""
Pydantic 请求 / 响应模型。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ==================== 统一日历查询 ====================

class CalendarItem(BaseModel):
    """统一查询返回的单条数据（爬虫或自定义事件合并后的结构）"""
    id: int
    source: str          # "news" 或 "event"，标识数据来源
    game: str
    title: str           # 爬虫的 info 或事件的 description
    link: str            # 爬虫有链接，事件为空字符串
    item_date: date      # 爬虫的 online_date 或事件的 event_date
    priority: int        # 标注/事件的优先级，无标注默认 0
    alias: str           # 标注/事件的别名，无标注默认空
    resource_ready: bool # 资源位
    hidden: bool         # 仅爬虫数据有，事件始终 False
    owners: List[str]    # 游戏负责人列表
    created_at: Optional[datetime] = None # 入库/创建时间（资讯速览使用）


class CalendarResponse(BaseModel):
    """统一日历查询响应"""
    total: int
    items: List[CalendarItem]


class HiddenListResponse(BaseModel):
    """已隐藏数据列表响应"""
    total: int
    items: List[CalendarItem]


# ==================== 游戏列表 ====================

class GamesListResponse(BaseModel):
    """游戏名称列表响应"""
    games: List[str]


# ==================== 标注 ====================

class AnnotationUpdate(BaseModel):
    """标注创建/更新请求体"""
    priority: Optional[int] = None         # 3/2/1/0
    alias: Optional[str] = None
    resource_ready: Optional[bool] = None
    hidden: Optional[bool] = None


class AnnotationResponse(BaseModel):
    """标注响应"""
    id: int
    news_id: int
    priority: int
    alias: str
    resource_ready: bool
    hidden: bool

    model_config = {"from_attributes": True}


# ==================== 自定义事件 ====================

class EventCreate(BaseModel):
    """事件创建请求体"""
    game: str
    description: str
    event_date: date
    priority: int = 0
    resource_ready: bool = False
    alias: str = ""


class EventUpdate(BaseModel):
    """事件更新请求体"""
    description: Optional[str] = None
    event_date: Optional[date] = None
    priority: Optional[int] = None
    resource_ready: Optional[bool] = None
    alias: Optional[str] = None


class EventResponse(BaseModel):
    """事件响应"""
    id: int
    game: str
    description: str
    event_date: date
    priority: int
    resource_ready: bool
    alias: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== 游戏负责人 ====================

class OwnerCreate(BaseModel):
    """负责人创建请求体"""
    game: str
    owners: List[str]


class OwnerUpdate(BaseModel):
    """负责人更新请求体"""
    owners: List[str]


class OwnerResponse(BaseModel):
    """负责人响应"""
    id: int
    game: str
    owners: List[str]

    model_config = {"from_attributes": True}


# ==================== 管理员认证 ====================

class AuthLoginRequest(BaseModel):
    """管理员密码登录请求体。"""
    password: str = Field(..., min_length=1)


class AuthLoginResponse(BaseModel):
    """管理员登录响应。"""
    token: str
    is_admin: bool
    auth_type: str
    expires_in: int


class AuthStatusResponse(BaseModel):
    """当前认证状态。"""
    is_admin: bool
    auth_type: Optional[str] = None
    expires_at: Optional[int] = None

