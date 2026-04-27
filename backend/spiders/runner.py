"""
爬虫批量执行入口（纯爬取，不依赖 app 模块）。

职责：
  1. 读 sites.yaml 配置
  2. 批量调用 BaseSpider 抓取
  3. 汇总结果 + 存 JSON 调试产物

本模块零 app 依赖，可独立测试爬虫逻辑，无需数据库。
完整流水线（含预处理 + 入库）见 backend.app.pipeline。

用法：
    # 项目根目录下（只爬取，不入库）
    .\.venv\Scripts\python.exe -m backend.spiders.runner
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

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
    print(f"调度间隔：每 {format_duration(cfg.schedule.interval_seconds)} 一次")
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
    """纯爬取入口：爬取 → 存 JSON，不入库。"""
    items = crawl_all()
    if items:
        save_preview(items)
    else:
        print("没有抓到任何数据，未生成预览文件。")


if __name__ == "__main__":
    main()
