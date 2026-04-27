"""
入库前预处理模块：筛选 + 日期提取。

职责：
  1. 从爬虫原始结果中筛选出标题含"X月X日"的条目
  2. 提取出 online_date（datetime.date），处理跨年（±6 个月窗口）
  3. 多个日期取第一个

本模块为独立可替换模块：
  - 输入：List[dict] 含 {"game", "info", "link"}
  - 输出：List[dict] 含 {"game", "info", "link", "online_date": date}
  - 未来可替换为 AI 版本，只需保持函数签名不变
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List

# 匹配"X月X日"，支持 1~2 位数字，不要求前导零
_DATE_PATTERN = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日")


def _infer_year(month: int, today: date) -> int:
    """
    根据标题月份和当前日期推断年份。
    使用 ±5 个月窗口：
      diff = title_month - current_month
      diff > 5  → 去年（旧闻方向）
      diff < -5 → 明年（跨年方向）
      else      → 今年
    """
    diff = month - today.month

    if diff > 5:
        return today.year - 1
    elif diff < -5:
        return today.year + 1
    else:
        return today.year


def _extract_date(text: str, today: date | None = None) -> date | None:
    """
    从文本中提取第一个"X月X日"并转为 date 对象。
    返回 None 表示未匹配到有效日期。
    """
    today = today or date.today()
    match = _DATE_PATTERN.search(text)
    if not match:
        return None

    month = int(match.group(1))
    day = int(match.group(2))

    # 基本范围校验
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None

    year = _infer_year(month, today)

    try:
        return date(year, month, day)
    except ValueError:
        # 非法日期（如 2月30日）
        return None


def preprocess(items: List[Dict[str, Any]],
               today: date | None = None) -> List[Dict[str, Any]]:
    """
    入库前预处理：筛选含"X月X日"的条目，提取 online_date。

    Args:
        items: 爬虫原始结果 [{"game", "info", "link"}, ...]
        today: 可选，用于单元测试注入固定日期

    Returns:
        筛选后的结果 [{"game", "info", "link", "online_date": date}, ...]
        不含日期的条目被丢弃。
    """
    result: List[Dict[str, Any]] = []
    discarded = 0

    for item in items:
        online_date = _extract_date(item.get("info", ""), today)
        if online_date is None:
            discarded += 1
            continue

        result.append({
            "game": item["game"],
            "info": item["info"],
            "link": item["link"],
            "online_date": online_date,
        })

    print(f"预处理完成：输入 {len(items)} 条，保留 {len(result)} 条，丢弃 {discarded} 条")
    return result


if __name__ == "__main__":
    # 本地自检
    test_items = [
        {"game": "DNF", "info": "4月24日更新公告，新版本来袭", "link": "https://example.com/1"},
        {"game": "DNF", "info": "DNF十八周年庆典活动", "link": "https://example.com/2"},
        {"game": "火影", "info": "3月27日更新公告，踏春季开启", "link": "https://example.com/3"},
        {"game": "LOL", "info": "1月5日新赛季开启公告", "link": "https://example.com/4"},
        {"game": "LOL", "info": "12月25日冬季限定活动", "link": "https://example.com/5"},
    ]

    today = date(2026, 4, 27)
    filtered = preprocess(test_items, today=today)
    for item in filtered:
        print(f"  [{item['game']}] {item['online_date']} - {item['info']}")
