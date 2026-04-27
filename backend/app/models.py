"""
ORM 数据表模型。

game_news 表：存储从各游戏官网爬取的资讯条目。
  - 去重依据：UNIQUE(game, info)
  - 清理依据：online_date 过期 N 天后删除
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class GameNews(Base):
    __tablename__ = "game_news"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    info: Mapped[str] = mapped_column(String(500), nullable=False)
    link: Mapped[str] = mapped_column(String(1000), nullable=False)
    online_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("game", "info", name="uq_game_info"),
    )

    def __repr__(self) -> str:
        return f"<GameNews id={self.id} game={self.game!r} info={self.info[:30]!r} online_date={self.online_date}>"
