"""
爬虫配置加载器：读取 sites.yaml 并做基础校验。
返回结构化的 dataclass，供 runner.py / 未来的 scheduler.py 使用。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv
import yaml

# 默认配置文件路径：与本模块同目录下的 sites.yaml
DEFAULT_CONFIG_PATH = Path(__file__).with_name("sites.yaml")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

# ---------------- 间隔表达式解析 ----------------
# 支持的单位：m(分钟) / h(小时) / d(天)；最小单位为分钟
_UNIT_TO_SECONDS = {
    "m": 60,
    "h": 60 * 60,
    "d": 60 * 60 * 24,
}
_DURATION_RE = re.compile(r"^\s*(\d+)\s*([mhd])\s*$", re.IGNORECASE)


def parse_duration(value: str | int) -> int:
    """
    把配置里的间隔表达式解析为秒数。

    支持格式：
      "30m" -> 1800
      "2h"  -> 7200
      "1d"  -> 86400
    也兼容纯整数（按分钟处理，例如 30 视为 30m）。

    非法输入抛 ValueError，信息清晰定位。
    """
    if isinstance(value, int):
        if value <= 0:
            raise ValueError(f"interval 必须为正数，收到 {value}")
        # 兼容 YAML 里直接写整数的情况，按分钟解释
        return value * _UNIT_TO_SECONDS["m"]

    if not isinstance(value, str):
        raise ValueError(f"interval 类型非法，应为字符串（如 '30m'），收到 {type(value).__name__}")

    match = _DURATION_RE.match(value)
    if not match:
        raise ValueError(
            f"interval 格式非法：{value!r}；应形如 '30m' / '2h' / '1d'（最小单位分钟）"
        )

    num = int(match.group(1))
    unit = match.group(2).lower()
    if num <= 0:
        raise ValueError(f"interval 数值必须为正数，收到 {value!r}")

    return num * _UNIT_TO_SECONDS[unit]


def format_duration(seconds: int) -> str:
    """把秒数格式化成人类易读字符串，仅用于日志展示。"""
    if seconds % _UNIT_TO_SECONDS["d"] == 0:
        return f"{seconds // _UNIT_TO_SECONDS['d']} 天"
    if seconds % _UNIT_TO_SECONDS["h"] == 0:
        return f"{seconds // _UNIT_TO_SECONDS['h']} 小时"
    if seconds % _UNIT_TO_SECONDS["m"] == 0:
        return f"{seconds // _UNIT_TO_SECONDS['m']} 分钟"
    return f"{seconds} 秒"


# ---------------- 数据类 ----------------
@dataclass
class ScheduleConfig:
    # 内部统一以秒存储，避免后续代码到处做单位换算
    interval_seconds: int = 2 * 60 * 60  # 默认 2 小时


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


# ---------------- 加载入口 ----------------
def load_sites_config(path: Path | str | None = None) -> SpiderConfig:
    """
    加载并校验 sites.yaml。
    - path 不传则使用与本模块同目录下的 sites.yaml
    - 字段缺失或格式非法会抛 ValueError / FileNotFoundError，定位清晰
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"爬虫配置文件不存在：{cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # schedule
    _ = load_dotenv(ENV_PATH, override=False)
    sched_raw = raw.get("schedule") or {}
    interval_raw = os.getenv("SPIDER_INTERVAL", "").strip() or sched_raw.get("interval", "2h")
    schedule = ScheduleConfig(
        interval_seconds=parse_duration(interval_raw),
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
    print(f"调度间隔: {format_duration(cfg.schedule.interval_seconds)} "
          f"({cfg.schedule.interval_seconds} 秒)")
    print(f"运行参数: {cfg.runtime}")
    print(f"站点总数: {len(cfg.sites)}，启用: {len(cfg.enabled_sites)}")
    for s in cfg.sites:
        flag = "ON " if s.enabled else "OFF"
        print(f"  [{flag}] {s.game} (parser={s.parser}) -> {s.url}")

