"""
FastAPI 应用入口。

启动时：
  1. 初始化数据库（建表）
  2. 启动 APScheduler 定时任务

用法（项目根目录下）：
  .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000

接口文档：
  http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.annotations import router as annotations_router
from backend.app.api.auth import router as auth_router
from backend.app.api.events import router as events_router
from backend.app.api.news import router as news_router
from backend.app.api.owners import router as owners_router
from backend.app.database import init_db
from backend.app.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期：启动时初始化，关闭时清理。"""
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="游戏时间轴看板 API",
    description="多游戏资讯聚合查询 + 标注 + 自定义事件 + 负责人管理",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(auth_router)
app.include_router(news_router)
app.include_router(annotations_router)
app.include_router(events_router)
app.include_router(owners_router)


@app.get("/", tags=["health"])
def health_check():
    """健康检查"""
    return {"status": "ok", "message": "游戏时间轴看板 API 运行中"}
