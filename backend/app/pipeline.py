"""
完整数据流水线：爬取 → 预处理 → 入库。

编排 spiders 模块和 app 模块，将两者串联起来。
本文件是手动跑完整流程、以及 scheduler 定时触发的统一入口。

用法：
    # 项目根目录下（爬取 + 预处理 + 入库）
    .\.venv\Scripts\python.exe -m backend.app.pipeline
"""

from __future__ import annotations

from backend.app.crud import bulk_insert_new
from backend.app.database import SessionLocal, init_db
from backend.app.preprocessor import preprocess
from backend.spiders.runner import crawl_all, save_preview


def run_pipeline() -> None:
    """爬取 → 预处理 → 入库 → 存 JSON 调试产物。"""
    # 1. 爬取
    raw_items = crawl_all()
    if not raw_items:
        print("没有抓到任何数据，流程结束。")
        return

    # 2. 预处理：筛选 + 提取 online_date
    filtered_items = preprocess(raw_items)
    if not filtered_items:
        print("预处理后无有效数据（没有标题包含日期），流程结束。")
        return

    # 3. 入库（去重）
    db = SessionLocal()
    try:
        bulk_insert_new(db, filtered_items)
    finally:
        db.close()

    # 4. 保存调试产物
    save_preview(filtered_items)

    print("\n" + "=" * 60)
    print("全流程完成")
    print("=" * 60)


def main() -> None:
    """手动执行入口：先建表再跑流水线。"""
    init_db()
    run_pipeline()


if __name__ == "__main__":
    main()
