"""
爬虫批量执行入口。

完整流水线：
  1. 读 sites.yaml 配置
  2. 批量调用 BaseSpider 抓取
  3. 预处理：筛选含日期的标题 + 提取 online_date
  4. 去重入库（SQLite / MySQL）
  5. 可选：保存 JSON 调试产物

用法：
    # 项目根目录下
    .\.venv\Scripts\python.exe -m backend.spiders.runner
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from backend.app.crud import bulk_insert_new
from backend.app.database import SessionLocal, init_db
from backend.app.preprocessor import preprocess
from backend.spiders.base import BaseSpider
from backend.spiders.config import SpiderConfig, format_duration, load_sites_config

# 调试产物目录（.gitignore 中 data/* 已忽略）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREVIEW_FILE = PROJECT_ROOT / "data" / "crawl_preview.json"


def crawl_all(cfg: SpiderConfig | None = None) -> List[Dict[str, Any]]:
    """
    按配置批量爬取所有启用的站点。
    返回：所有站点合并后的原始 item 列表。
    """
    cfg = cfg or load_sites_config()
    enabled = cfg.enabled_sites

    print("=" * 60)
    print(f"爬虫启动：共 {len(cfg.sites)} 个站点，启用 {len(enabled)} 个")
    print(f"调度间隔（本轮未启用）：每 {format_duration(cfg.schedule.interval_seconds)} 一次")
    print(f"运行参数：headless={cfg.runtime.headless}, "
          f"timeout={cfg.runtime.timeout_seconds}s, retry={cfg.runtime.retry_times}")
    print("=" * 60)

    all_items: List[Dict[str, Any]] = []

    with BaseSpider(
        ignore_https_errors=cfg.runtime.ignore_https_errors,
        headless=cfg.runtime.headless,
        timeout=cfg.runtime.timeout_seconds,
        retry_times=cfg.runtime.retry_times,
    ) as spider:
        for site in enabled:
            print(f"\n>>> [{site.game}] 开始爬取：{site.url}")
            items = spider.run(site.parser, site.url)

            # 用配置里的 game 覆盖解析器返回的默认值
            for item in items:
                item["game"] = site.game

            all_items.extend(items)
            print(f"<<< [{site.game}] 完成，本站点 {len(items)} 条")

    print("\n" + "=" * 60)
    print(f"爬取汇总：共抓到 {len(all_items)} 条原始数据")
    print("=" * 60)

    return all_items


def save_preview(items: List[Dict[str, Any]], path: Path = PREVIEW_FILE) -> None:
    """将结果写入本地 JSON，便于肉眼检查。"""
    path.parent.mkdir(parents=True, exist_ok=True)

    # date 对象序列化为字符串
    def _serialize(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    payload = {
        "crawled_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=_serialize)
    print(f"调试产物已写入：{path}")


def main() -> None:
    """完整流水线：爬取 → 预处理 → 入库。"""
    # 确保数据库表存在
    init_db()

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

    # 4. 保存调试产物（预处理后的数据）
    save_preview(filtered_items)

    print("\n" + "=" * 60)
    print("全流程完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
