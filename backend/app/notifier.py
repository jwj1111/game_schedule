"""
企微 Webhook 定时推送模块。

职责：
  - 查询数据库，组装 markdown 消息
  - 发送到企微群机器人

可插拔设计：
  - 本模块不被其他模块 import（仅 scheduler 注册时引用）
  - WECOM_WEBHOOK 为空时静默跳过
  - 删除本文件 + scheduler 注册代码，项目照常运行

独立测试：
  python -m backend.app.notifier
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List

import requests
from sqlalchemy.orm import Session

from backend.app.config import PUSH_SITE_URL, WECOM_WEBHOOK
from backend.app.database import SessionLocal
from backend.app.models import GameNews, GameOwner, UserEvent

# Markdown 消息最大字节数（留 100 字节余量给截断提示）
_MAX_BYTES = 3900


# ==================== 底层：发送 ====================

def send_markdown(content: str) -> dict | None:
    """发送 markdown 消息到企微 webhook。WECOM_WEBHOOK 为空时跳过。"""
    if not WECOM_WEBHOOK:
        print("[推送] WECOM_WEBHOOK 未配置，跳过")
        return None

    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    try:
        resp = requests.post(WECOM_WEBHOOK, json=payload, timeout=10)
        result = resp.json()
        if result.get("errcode") != 0:
            print(f"[推送] 发送失败: {result}")
        else:
            print("[推送] 发送成功")
        return result
    except Exception as e:
        print(f"[推送] 请求异常: {e}")
        return None


# ==================== 中层：查询 + 组装 ====================

def _query_due_items(db: Session) -> List[dict]:
    """查询未来7天到期的重点未配置事项（priority>0 && !resource_ready && !hidden）。"""
    today = date.today()
    end = today + timedelta(days=6)

    items = []

    # 爬虫数据
    for news in db.query(GameNews).filter(
        GameNews.online_date >= today,
        GameNews.online_date <= end,
    ).all():
        ann = news.annotation
        if not ann or ann.hidden:
            continue
        if ann.priority > 0 and not ann.resource_ready:
            items.append({
                "game": news.game,
                "title": ann.alias or news.info,
                "date": news.online_date,
            })

    # 手动事件
    for event in db.query(UserEvent).filter(
        UserEvent.event_date >= today,
        UserEvent.event_date <= end,
    ).all():
        if event.priority > 0 and not event.resource_ready:
            items.append({
                "game": event.game,
                "title": event.alias or event.description,
                "date": event.event_date,
            })

    items.sort(key=lambda x: x["date"])
    return items


def _query_expired_items(db: Session) -> List[dict]:
    """查询过去7天过期未配置事项。"""
    today = date.today()
    start = today - timedelta(days=7)

    items = []

    for news in db.query(GameNews).filter(
        GameNews.online_date >= start,
        GameNews.online_date < today,
    ).all():
        ann = news.annotation
        if not ann or ann.hidden:
            continue
        if ann.priority > 0 and not ann.resource_ready:
            items.append({
                "game": news.game,
                "title": ann.alias or news.info,
                "date": news.online_date,
            })

    for event in db.query(UserEvent).filter(
        UserEvent.event_date >= start,
        UserEvent.event_date < today,
    ).all():
        if event.priority > 0 and not event.resource_ready:
            items.append({
                "game": event.game,
                "title": event.alias or event.description,
                "date": event.event_date,
            })

    items.sort(key=lambda x: x["date"])
    return items


def _query_new_items(db: Session) -> List[dict]:
    """查询过去24h入库的未处理爬虫数据（priority=0 + 未隐藏 + 未配置资源位）。"""
    now = datetime.now()
    since = now - timedelta(hours=24)

    items = []
    for news in db.query(GameNews).filter(
        GameNews.created_at >= since,
        GameNews.created_at <= now,
    ).all():
        ann = news.annotation
        # 有标注且已处理过（优先级非0 / 已隐藏 / 已配置资源位）→ 跳过
        if ann and (ann.priority != 0 or ann.hidden or ann.resource_ready):
            continue
        items.append({
            "game": news.game,
            "title": news.info,
            "date": news.online_date,
        })

    items.sort(key=lambda x: x["date"])
    return items


def _get_owner_map(db: Session) -> Dict[str, List[str]]:
    """获取游戏 → userid 列表的映射。"""
    return {o.game: o.owners for o in db.query(GameOwner).all()}


def _format_section(title: str, items: List[dict], owner_map: Dict[str, List[str]], at_owners: bool = True) -> str:
    """格式化一个推送板块。扁平列表，最多显示4条。"""
    if not items:
        return ""

    total = len(items)
    show_items = items[:4]

    lines = [f"**{title}（{total}条）**"]

    mentioned_userids = set()

    # 收集所有条目的负责人（不仅是显示的）
    if at_owners:
        for item in items:
            for uid in owner_map.get(item["game"], []):
                mentioned_userids.add(uid)

    for item in show_items:
        lines.append(f">**{item['game']}**：{item['title']}")

    if total > 4:
        lines.append(f"<font color=\"comment\">…还有 {total - 4} 条，请查看看板</font>")

    # @ 负责人
    if at_owners and mentioned_userids:
        lines.append("")
        at_str = " ".join(f"<@{uid}>" for uid in sorted(mentioned_userids))
        lines.append(at_str)

    return "\n".join(lines)


def build_message(db: Session) -> str | None:
    """查询数据库，组装完整推送消息。所有板块为空时返回 None。"""
    owner_map = _get_owner_map(db)

    due_items = _query_due_items(db)
    expired_items = _query_expired_items(db)
    new_items = _query_new_items(db)

    # 全部为空则不推送
    if not due_items and not expired_items and not new_items:
        return None

    parts = []

    parts.append("## 游戏日历 · 定时提醒")
    parts.append("")

    # 收集各板块（只对有数据的板块编号，带颜色）
    section_num = 0

    # 未来7天到期（橙红色）
    section = _format_section("未来7天到期", due_items, owner_map, at_owners=True)
    if section:
        section_num += 1
        parts.append(section.replace(
            "**未来7天到期",
            f"**<font color=\"warning\">{section_num}. 未来7天到期</font>", 1
        ))
        parts.append("")

    # 过期未配置（橙红色）
    section = _format_section("过期未配置", expired_items, owner_map, at_owners=True)
    if section:
        section_num += 1
        parts.append(section.replace(
            f"**过期未配置",
            f"**<font color=\"warning\">{section_num}. 过期未配置</font>", 1
        ))
        parts.append("")

    # 最新事件（绿色）
    section = _format_section("最新事件", new_items, owner_map, at_owners=True)
    if section:
        section_num += 1
        parts.append(section.replace(
            f"**最新事件",
            f"**<font color=\"info\">{section_num}. 最新事件</font>", 1
        ))

    # 底部：看板链接
    if PUSH_SITE_URL:
        parts.append("")
        parts.append(f"[查看详情 →]({PUSH_SITE_URL})")

    content = "\n".join(parts)

    # 截断处理
    encoded = content.encode("utf-8")
    if len(encoded) > _MAX_BYTES:
        truncated = encoded[:_MAX_BYTES].decode("utf-8", errors="ignore")
        # 找最后一个完整行
        last_newline = truncated.rfind("\n")
        if last_newline > 0:
            truncated = truncated[:last_newline]
        content = truncated + "\n\n> …内容过长已截断，请查看看板"

    return content


# ==================== 入口 ====================

def push_notify():
    """执行一次推送（供 scheduler 定时调用或手动执行）。"""
    if not WECOM_WEBHOOK:
        print("[推送] WECOM_WEBHOOK 未配置，跳过")
        return

    db = SessionLocal()
    try:
        content = build_message(db)
        if content is None:
            print("[推送] 所有板块为空，跳过本次推送")
            return
        send_markdown(content)
    finally:
        db.close()


def main():
    """手动测试入口。"""
    from backend.app.database import init_db
    init_db()
    print("[推送] 手动触发推送...")
    try:
        push_notify()
    except Exception as e:
        print(f"[推送] 执行异常: {e}")


if __name__ == "__main__":
    main()
