"""
SQLAlchemy 数据库会话管理。

提供:
  - engine: 数据库引擎（SQLite / MySQL 由 config.py 自动切换）
  - SessionLocal: 会话工厂
  - Base: ORM 声明基类
  - get_db(): FastAPI 依赖注入用的生成器
  - init_db(): 首次运行建表
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.config import DATABASE_URL, ENV

# SQLite 需要 check_same_thread=False 才能在多线程中使用
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖注入：每个请求一个 Session，用完自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """根据 ORM 模型创建所有表（已存在的表不会重建）。"""
    Base.metadata.create_all(bind=engine)
    print(f"数据库初始化完成 (env={ENV}, url={DATABASE_URL})")
