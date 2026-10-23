# -*- coding: utf-8 -*-
"""数据源接入与内容库轮换 —— 对应需求文档第 8 章。
所有条目均来自公开可访问来源，仅做截断与清洗，禁止改写或生成正文。"""
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from PySide6.QtCore import QThread, Signal

UA = "TodayFrontier/0.1 (desktop widget)"

# PyInstaller 打包后 __file__ 指向临时解压目录，内置库随包解压在 sys._MEIPASS 下
if getattr(sys, "frozen", False):
    ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_DIR = os.path.join(ROOT, "resources")

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/%d.json"
ARXIV = ("http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG"
         "&sortBy=submittedDate&sortOrder=descending&max_results=10")
GITHUB_TRENDING = "https://github.com/trending?since=daily"


def _get(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _item(kind, title, summary, tags, source_name, source_url, published=None):
    return {
        "id": "",
        "type": kind,
        "title": _clean(title)[:40],
        "summary": _clean(summary)[:100],
        "tags": list(tags or []),
        "source_name": source_name,
        "source_url": source_url,
        "published_at": published,
        "pushed_date": date.today().isoformat(),
        "read": False,
        "favorite": False,
    }


# ---------------- Hacker News ----------------
def fetch_hacker_news(limit=6):
    ids = json.loads(_get(HN_TOP))[: limit * 3]

    def one(i):
        try:
            d = json.loads(_get(HN_ITEM % i, timeout=6))
        except Exception:
            return None
        if not d or d.get("type") != "story" or not d.get("title"):
            return None
        url = d.get("url") or ("https://news.ycombinator.com/item?id=%d" % i)
        domain = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        return _item("news", d.get("title"),
                     "%s · %d 分 · %d 条讨论" % (domain, d.get("score", 0), d.get("descendants", 0)),
                     [], "Hacker News", url)

    with ThreadPoolExecutor(max_workers=4) as ex:
        out = [x for x in ex.map(one, ids) if x]
    return out[:limit]


# ---------------- arXiv ----------------
def fetch_arxiv(limit=4):
    xmlns = "{http://www.w3.org/2005/Atom}"
    try:
        root = ET.fromstring(_get(ARXIV, timeout=10))
    except Exception:
        return []
    out = []
    for e in root.findall(xmlns + "entry"):
        title = (e.findtext(xmlns + "title") or "").strip()
        summary = (e.findtext(xmlns + "summary") or "").strip()
        url = (e.findtext(xmlns + "id") or "").strip()
        if not (title and url):
            continue
        out.append(_item("news", title, summary, ["arXiv"], "arXiv", url))
        if len(out) >= limit:
            break
    return out


# ---------------- GitHub Trending ----------------
def fetch_github_trending(limit=4):
    try:
        page = _get(GITHUB_TRENDING, timeout=10)
    except Exception:
        return []
    out = []
    for block in re.findall(r"<article[^>]*>(.*?)</article>", page, re.S):
        m = re.search(r'<h2[^>]*>.*?href="/([^"/]+/[^"]+)"', block, re.S)
        if not m:
            continue
        repo = m.group(1)
        d = re.search(r'<p class="col-9[^"]*"[^>]*>(.*?)</p>', block, re.S)
        lang = re.search(r'itemprop="programmingLanguage">([^<]+)<', block)
        tags = [lang.group(1).strip()] if lang else []
        out.append(_item("framework", repo, d.group(1) if d else "", tags,
                         "GitHub Trending", "https://github.com/" + repo))
        if len(out) >= limit:
            break
    return out


# ---------------- 内置算法 / 框架库 ----------------
def load_library(kind):
    name = "algorithms.json" if kind == "algorithm" else "frameworks.json"
    p = os.path.join(RESOURCE_DIR, name)
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def pick_from_library(kind, seq):
    """按序号轮换，轮尽后回到第 1 条；不改写原文，仅取字段。"""
    lib = load_library(kind)
    if not lib:
        return None
    e = lib[seq % len(lib)]
    return _item(kind, e.get("name", ""), e.get("summary", ""),
                 e.get("tags", []), e.get("source_name", "内置库"), e.get("url", ""))


# ---------------- 抓取线程 ----------------
class FetchWorker(QThread):
    """在子线程并发拉取各数据源，避免阻塞 UI。"""
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, enabled_types, parent=None):
        super().__init__(parent)
        self.enabled_types = enabled_types

    def run(self):
        tasks = []
        if "news" in self.enabled_types:
            tasks.append(("news", fetch_hacker_news))
            tasks.append(("news", fetch_arxiv))
        if "framework" in self.enabled_types:
            tasks.append(("framework", fetch_github_trending))
        if not tasks:
            self.finished.emit([])
            return

        results, errors = [], []
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(fn): label for label, fn in tasks}
            for fut, label in futures.items():
                try:
                    results.extend(fut.result(timeout=15))
                except Exception as exc:
                    errors.append("%s: %s" % (label, exc))
        if not results and errors:
            self.failed.emit("；".join(errors)[:120])
        else:
            self.finished.emit(results)
