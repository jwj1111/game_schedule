"""
自定义事件 CRUD 路由。

接口：
  POST   /api/events          新建事件
  PUT    /api/events/{id}     修改事件
  DELETE /api/events/{id}     删除事件（物理删除）
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.crud import create_event, delete_event, update_event
from backend.app.database import get_db
from backend.app.schemas import EventCreate, EventResponse, EventUpdate

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=201)
def add_event(body: EventCreate, db: Session = Depends(get_db)):
    """新建自定义事件。"""
    event = create_event(db, body.model_dump())
    return event


@router.put("/{event_id}", response_model=EventResponse)
def modify_event(event_id: int, body: EventUpdate, db: Session = Depends(get_db)):
    """修改自定义事件。"""
    event = update_event(db, event_id, body.model_dump(exclude_unset=True))
    if event is None:
        raise HTTPException(status_code=404, detail="事件不存在")
    return event


@router.delete("/{event_id}", status_code=204)
def remove_event(event_id: int, db: Session = Depends(get_db)):
    """删除自定义事件（物理删除）。"""
    ok = delete_event(db, event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="事件不存在")
