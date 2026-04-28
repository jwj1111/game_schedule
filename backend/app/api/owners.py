"""
游戏负责人管理路由。

接口：
  GET  /api/owners           全部游戏负责人
  GET  /api/owners/{game}    单个游戏负责人
  POST /api/owners           新增游戏负责人
  PUT  /api/owners/{game}    修改负责人列表
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.crud import create_owner, get_all_owners, get_owner_by_game, update_owner
from backend.app.database import get_db
from backend.app.schemas import OwnerCreate, OwnerResponse, OwnerUpdate

router = APIRouter(prefix="/api/owners", tags=["owners"])


@router.get("", response_model=List[OwnerResponse])
def list_owners(db: Session = Depends(get_db)):
    """全部游戏负责人列表。"""
    return get_all_owners(db)


@router.get("/{game}", response_model=OwnerResponse)
def get_game_owner(game: str, db: Session = Depends(get_db)):
    """查询单个游戏的负责人。"""
    record = get_owner_by_game(db, game)
    if record is None:
        raise HTTPException(status_code=404, detail="该游戏暂无负责人")
    return record


@router.post("", response_model=OwnerResponse, status_code=201)
def add_owner(body: OwnerCreate, db: Session = Depends(get_db)):
    """新增游戏负责人。"""
    existing = get_owner_by_game(db, body.game)
    if existing:
        raise HTTPException(status_code=409, detail="该游戏负责人已存在，请用 PUT 修改")
    return create_owner(db, body.game, body.owners)


@router.put("/{game}", response_model=OwnerResponse)
def modify_owner(game: str, body: OwnerUpdate, db: Session = Depends(get_db)):
    """修改负责人列表。"""
    record = update_owner(db, game, body.owners)
    if record is None:
        raise HTTPException(status_code=404, detail="该游戏负责人不存在")
    return record
