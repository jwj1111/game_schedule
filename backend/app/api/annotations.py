"""
标注操作路由（针对爬虫数据的附加属性）。

接口：
  GET /api/annotations/{news_id}    获取标注
  PUT /api/annotations/{news_id}    创建或更新标注
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth import require_admin
from backend.app.crud import get_annotation, upsert_annotation
from backend.app.database import get_db
from backend.app.models import GameNews
from backend.app.schemas import AnnotationResponse, AnnotationUpdate

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


@router.get("/{news_id}", response_model=AnnotationResponse)
def get_news_annotation(news_id: int, db: Session = Depends(get_db)):
    """获取某条爬虫数据的标注。"""
    # 确认爬虫数据存在
    if not db.query(GameNews.id).filter(GameNews.id == news_id).first():
        raise HTTPException(status_code=404, detail="爬虫数据不存在")

    ann = get_annotation(db, news_id)
    if ann is None:
        raise HTTPException(status_code=404, detail="该条数据暂无标注")
    return ann


@router.put("/{news_id}", response_model=AnnotationResponse)
def update_news_annotation(
    news_id: int,
    body: AnnotationUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """创建或更新标注（优先级/别名/资源位/隐藏）。"""
    if not db.query(GameNews.id).filter(GameNews.id == news_id).first():
        raise HTTPException(status_code=404, detail="爬虫数据不存在")

    ann = upsert_annotation(db, news_id, body.model_dump(exclude_unset=True))
    return ann
