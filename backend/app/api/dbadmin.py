"""
数据库可视化管理接口（彩蛋功能）。

所有接口均需管理员权限。
通过 SQLAlchemy Inspector 读取表结构，自动适配 SQLite / MySQL。
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import inspect as sa_inspect, select, insert, update, delete, func
from sqlalchemy import Boolean, Date, DateTime, Integer, Float, JSON, MetaData, Table
from sqlalchemy.orm import Session

from backend.app.auth import require_admin
from backend.app.config import ENV, DATA_RETENTION_DAYS
from backend.app.database import engine, get_db, Base
from backend.app.scheduler import get_scheduler_info

router = APIRouter(prefix="/api/dbadmin", tags=["dbadmin"], dependencies=[Depends(require_admin)])


def _coerce_value(column, value):
    """根据列类型将前端传入的字符串值转为 Python 对应类型。"""
    if value is None:
        return None

    col_type = type(column.type)

    # Date 类型 → Python date 对象
    if col_type is Date or issubclass(col_type, Date):
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                parts = value.strip().split("-")
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, TypeError, IndexError):
                return value
        return value

    # DateTime 类型 → Python datetime 对象
    if col_type is DateTime or issubclass(col_type, DateTime):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # 支持 "2026-04-29 16:24:05.637068" 或 ISO 格式
            try:
                cleaned = value.strip().replace("T", " ")
                return datetime.fromisoformat(cleaned)
            except (ValueError, TypeError):
                return value
        return value

    # Boolean 类型
    if col_type is Boolean or issubclass(col_type, Boolean):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    # Integer 类型
    if col_type is Integer or issubclass(col_type, Integer):
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (ValueError, TypeError):
            return value

    # Float 类型
    if col_type is Float or issubclass(col_type, Float):
        if isinstance(value, float):
            return value
        try:
            return float(value)
        except (ValueError, TypeError):
            return value

    # JSON 类型
    if col_type is JSON or issubclass(col_type, JSON):
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return value

    # 其他（String/Text 等）直接返回
    return value


def _coerce_row_data(table, data: dict[str, Any]) -> dict[str, Any]:
    """对整行数据做类型转换。"""
    result = {}
    col_map = {c.name: c for c in table.columns}
    for k, v in data.items():
        if k in col_map:
            result[k] = _coerce_value(col_map[k], v)
        else:
            result[k] = v
    return result


@router.get("/tables")
def list_tables() -> dict[str, Any]:
    """列出所有数据表名称。"""
    inspector = sa_inspect(engine)
    tables = inspector.get_table_names()
    return {"tables": tables}


@router.get("/tables/{table_name}/schema")
def get_table_schema(table_name: str) -> dict[str, Any]:
    """获取指定表的列结构信息。"""
    inspector = sa_inspect(engine)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"表 '{table_name}' 不存在")

    columns = inspector.get_columns(table_name)
    pk = inspector.get_pk_constraint(table_name)
    pk_columns = pk.get("constrained_columns", []) if pk else []

    col_list = []
    for col in columns:
        col_list.append({
            "name": col["name"],
            "type": str(col["type"]),
            "nullable": col.get("nullable", True),
            "default": str(col["default"]) if col.get("default") is not None else None,
            "primary_key": col["name"] in pk_columns,
        })

    return {"table": table_name, "columns": col_list, "primary_keys": pk_columns}


@router.get("/tables/{table_name}/rows")
def get_table_rows(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort_by: str = Query(None),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """分页查询表数据。"""
    inspector = sa_inspect(engine)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"表 '{table_name}' 不存在")

    # 通过 metadata 反射获取表对象
    meta = Base.metadata
    if table_name not in meta.tables:
        # 表不在 ORM 声明中，动态反射
        temp_meta = MetaData()
        table = Table(table_name, temp_meta, autoload_with=engine)
    else:
        table = meta.tables[table_name]

    # 总数
    count_result = db.execute(select(func.count()).select_from(table))
    total = count_result.scalar() or 0

    # 构建查询
    query = select(table)

    # 排序
    if sort_by and sort_by in [c.name for c in table.columns]:
        col = table.c[sort_by]
        query = query.order_by(col.desc() if sort_order == "desc" else col.asc())
    else:
        # 默认按主键排序
        pk_cols = [c for c in table.columns if c.primary_key]
        if pk_cols:
            query = query.order_by(pk_cols[0].desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)

    result = db.execute(query)
    rows = []
    for row in result:
        row_dict = {}
        for i, col in enumerate(table.columns):
            val = row[i]
            # 序列化特殊类型
            if val is not None and not isinstance(val, (str, int, float, bool)):
                val = str(val)
            row_dict[col.name] = val
        rows.append(row_dict)

    return {
        "table": table_name,
        "rows": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.post("/tables/{table_name}/rows")
def create_row(
    table_name: str,
    row_data: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """新增一行数据。"""
    inspector = sa_inspect(engine)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"表 '{table_name}' 不存在")

    meta = Base.metadata
    if table_name not in meta.tables:
        temp_meta = MetaData()
        table = Table(table_name, temp_meta, autoload_with=engine)
    else:
        table = meta.tables[table_name]

    # 过滤掉自增主键和空值
    valid_columns = {c.name for c in table.columns}
    filtered = {k: v for k, v in row_data.items() if k in valid_columns and v is not None}

    if not filtered:
        raise HTTPException(status_code=400, detail="没有有效的字段数据")

    # 类型转换（字符串 → date/datetime/bool/int 等）
    filtered = _coerce_row_data(table, filtered)

    try:
        result = db.execute(insert(table).values(**filtered))
        db.commit()
        return {"success": True, "inserted_id": result.inserted_primary_key[0] if result.inserted_primary_key else None}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"插入失败: {e}")


@router.put("/tables/{table_name}/rows/{row_id}")
def update_row(
    table_name: str,
    row_id: int,
    row_data: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """修改一行数据（按主键 id）。"""
    inspector = sa_inspect(engine)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"表 '{table_name}' 不存在")

    meta = Base.metadata
    if table_name not in meta.tables:
        temp_meta = MetaData()
        table = Table(table_name, temp_meta, autoload_with=engine)
    else:
        table = meta.tables[table_name]

    # 找主键列
    pk_cols = [c for c in table.columns if c.primary_key]
    if not pk_cols:
        raise HTTPException(status_code=400, detail="该表没有主键，无法按 ID 更新")

    pk_col = pk_cols[0]
    valid_columns = {c.name for c in table.columns}
    filtered = {k: v for k, v in row_data.items() if k in valid_columns and k != pk_col.name}

    if not filtered:
        raise HTTPException(status_code=400, detail="没有可更新的字段")

    # 类型转换（字符串 → date/datetime/bool/int 等）
    filtered = _coerce_row_data(table, filtered)

    try:
        result = db.execute(update(table).where(pk_col == row_id).values(**filtered))
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"未找到 {pk_col.name}={row_id} 的记录")
        return {"success": True, "updated": result.rowcount}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"更新失败: {e}")


@router.delete("/tables/{table_name}/rows/{row_id}")
def delete_row(
    table_name: str,
    row_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """删除一行数据（按主键 id）。"""
    inspector = sa_inspect(engine)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"表 '{table_name}' 不存在")

    meta = Base.metadata
    if table_name not in meta.tables:
        temp_meta = MetaData()
        table = Table(table_name, temp_meta, autoload_with=engine)
    else:
        table = meta.tables[table_name]

    pk_cols = [c for c in table.columns if c.primary_key]
    if not pk_cols:
        raise HTTPException(status_code=400, detail="该表没有主键，无法按 ID 删除")

    pk_col = pk_cols[0]

    try:
        result = db.execute(delete(table).where(pk_col == row_id))
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"未找到 {pk_col.name}={row_id} 的记录")
        return {"success": True, "deleted": result.rowcount}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"删除失败: {e}")


@router.post("/tables/{table_name}/rows/batch-delete")
def batch_delete_rows(
    table_name: str,
    body: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """批量删除多行数据（按主键 id 列表）。"""
    ids = body.get("ids", [])
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="ids 必须是非空数组")
    if len(ids) > 500:
        raise HTTPException(status_code=400, detail="单次最多删除 500 条")

    inspector = sa_inspect(engine)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"表 '{table_name}' 不存在")

    meta = Base.metadata
    if table_name not in meta.tables:
        temp_meta = MetaData()
        table = Table(table_name, temp_meta, autoload_with=engine)
    else:
        table = meta.tables[table_name]

    pk_cols = [c for c in table.columns if c.primary_key]
    if not pk_cols:
        raise HTTPException(status_code=400, detail="该表没有主键，无法批量删除")

    pk_col = pk_cols[0]

    try:
        result = db.execute(delete(table).where(pk_col.in_(ids)))
        db.commit()
        return {"success": True, "deleted": result.rowcount}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"批量删除失败: {e}")


@router.get("/status")
def system_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    """系统运行状态：调度器 + 数据库 + 服务器信息。"""

    # ---- 调度器状态 ----
    scheduler_info = get_scheduler_info()

    # ---- 数据库各表行数 ----
    table_counts = {}
    inspector = sa_inspect(engine)
    for tname in inspector.get_table_names():
        meta = Base.metadata
        if tname in meta.tables:
            table = meta.tables[tname]
        else:
            temp_meta = MetaData()
            table = Table(tname, temp_meta, autoload_with=engine)
        count = db.execute(select(func.count()).select_from(table)).scalar() or 0
        table_counts[tname] = count

    # ---- 服务器信息 ----
    server_info = {
        "env": ENV,
        "data_retention_days": DATA_RETENTION_DAYS,
    }

    return {
        "scheduler": scheduler_info,
        "database": table_counts,
        "server": server_info,
    }
