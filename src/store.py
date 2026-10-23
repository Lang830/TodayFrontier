# -*- coding: utf-8 -*-
"""内容缓存与去重 —— 对应需求文档 9.3 节。"""
import json
import os
from datetime import datetime, timedelta, date

from config import APP_DIR

KEEP_DAYS = 30


def _path():
    os.makedirs(APP_DIR, exist_ok=True)
    return os.path.join(APP_DIR, "cache.json")


def load_items():
    p = _path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_items(items):
    p = _path()
    tmp = p + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
        return True
    except OSError:
        return False


def prune(items):
    """保留最近 30 天；收藏项不受时间限制。"""
    cutoff = (date.today() - timedelta(days=KEEP_DAYS)).isoformat()
    kept = [i for i in items if i.get("favorite") or (i.get("pushed_date") or "") >= cutoff]
    seen = set()
    out = []
    for i in kept:
        url = i.get("source_url") or i.get("id")
        if url in seen:
            continue
        seen.add(url)
        out.append(i)
    return out


def add_batch(items, new_items):
    """以 source_url 为键去重，30 天内已推送过的条目跳过。"""
    existing = {i.get("source_url") for i in items}
    added = []
    for it in new_items:
        url = it.get("source_url")
        if not url or url in existing:
            continue
        existing.add(url)
        added.append(it)
    return added


def today_items(items, day=None):
    day = day or date.today().isoformat()
    return [i for i in items if i.get("pushed_date") == day]


def last_update_date(items):
    days = sorted({i.get("pushed_date") for i in items if i.get("pushed_date")}, reverse=True)
    return days[0] if days else None


def mark_read(items, item_id):
    for i in items:
        if i.get("id") == item_id:
            i["read"] = True
            return True
    return False


def stamp():
    return datetime.now().strftime("%Y-%m-%d")
