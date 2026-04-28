"""
ORM 数据表模型。

表：
  - game_news:        爬虫原始数据（只读，爬虫写入）
  - user_annotation:  用户标注（关联爬虫数据，附加优先级/别名/资源位/隐藏）
  - user_event:       用户自定义事件
  - game_owner:       游戏负责人映射
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer,
    JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class GameNews(Base):
    """爬虫原始表（只读）"""
    __tablename__ = "game_news"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    info: Mapped[str] = mapped_column(String(500), nullable=False)
    link: Mapped[str] = mapped_column(String(1000), nullable=False)
    online_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    # 一对一关联标注（可能没有）
    annotation = relationship("UserAnnotation", back_populates="news", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("game", "info", name="uq_game_info"),
    )

    def __repr__(self) -> str:
        return f"<GameNews id={self.id} game={self.game!r} info={self.info[:30]!r}>"


class UserAnnotation(Base):
    """用户标注表（关联爬虫数据）"""
    __tablename__ = "user_annotation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_news.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 3=高 2=中 1=低 0=无
    alias: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    resource_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    news = relationship("GameNews", back_populates="annotation")

    def __repr__(self) -> str:
        return f"<UserAnnotation id={self.id} news_id={self.news_id} priority={self.priority}>"


class UserEvent(Base):
    """用户自定义事件表"""
    __tablename__ = "user_event"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resource_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    alias: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __repr__(self) -> str:
        return f"<UserEvent id={self.id} game={self.game!r} desc={self.description[:30]!r}>"


class GameOwner(Base):
    """游戏负责人映射表"""
    __tablename__ = "game_owner"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    owners: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # ["张三", "李四"]

    def __repr__(self) -> str:
        return f"<GameOwner game={self.game!r} owners={self.owners}>"
