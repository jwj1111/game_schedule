"""
爬虫配置加载器：读取 sites.yaml 并做基础校验。
返回结构化的 dataclass，供 runner.py / 未来的 scheduler.py 使用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

# 默认配置文件路径：与本模块同目录下的 sites.yaml
DEFAULT_CONFIG_PATH = Path(__file__).with_name("sites.yaml")


@dataclass
class ScheduleConfig:
    interval_hours: int = 2


@dataclass
class RuntimeConfig:
    headless: bool = True
    ignore_https_errors: bool = False
    timeout_seconds: int = 15
    retry_times: int = 3


@dataclass
class SiteConfig:
    game: str
    parser: str
    url: str
    enabled: bool = True


@dataclass
class SpiderConfig:
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    sites: List[SiteConfig] = field(default_factory=list)

    @property
    def enabled_sites(self) -> List[SiteConfig]:
        return [s for s in self.sites if s.enabled]


def load_sites_config(path: Path | str | None = None) -> SpiderConfig:
    """
    加载并校验 sites.yaml。
    - path 不传则使用与本模块同目录下的 sites.yaml
    - 字段缺失会抛 ValueError，定位清晰
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"爬虫配置文件不存在：{cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # schedule
    sched_raw = raw.get("schedule") or {}
    schedule = ScheduleConfig(
        interval_hours=int(sched_raw.get("interval_hours", 2)),
    )

    # runtime
    rt_raw = raw.get("runtime") or {}
    runtime = RuntimeConfig(
        headless=bool(rt_raw.get("headless", True)),
        ignore_https_errors=bool(rt_raw.get("ignore_https_errors", False)),
        timeout_seconds=int(rt_raw.get("timeout_seconds", 15)),
        retry_times=int(rt_raw.get("retry_times", 3)),
    )

    # sites
    sites_raw = raw.get("sites") or []
    if not isinstance(sites_raw, list) or not sites_raw:
        raise ValueError("sites.yaml 中 sites 列表不能为空")

    sites: List[SiteConfig] = []
    for idx, item in enumerate(sites_raw):
        if not isinstance(item, dict):
            raise ValueError(f"sites[{idx}] 必须是对象")
        for key in ("game", "parser", "url"):
            if not item.get(key):
                raise ValueError(f"sites[{idx}] 缺少必填字段：{key}")
        sites.append(SiteConfig(
            game=str(item["game"]).strip(),
            parser=str(item["parser"]).strip(),
            url=str(item["url"]).strip(),
            enabled=bool(item.get("enabled", True)),
        ))

    return SpiderConfig(schedule=schedule, runtime=runtime, sites=sites)


if __name__ == "__main__":
    # 本地快速自检
    cfg = load_sites_config()
    print(f"调度间隔: {cfg.schedule.interval_hours} 小时")
    print(f"运行参数: {cfg.runtime}")
    print(f"站点总数: {len(cfg.sites)}，启用: {len(cfg.enabled_sites)}")
    for s in cfg.sites:
        flag = "ON " if s.enabled else "OFF"
        print(f"  [{flag}] {s.game} (parser={s.parser}) -> {s.url}")
