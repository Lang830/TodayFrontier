# -*- coding: utf-8 -*-
"""应用配置读写 —— 对应需求文档 9.2 节 config.json。"""
import json
import os
import tempfile

APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "TodayFrontier")

DEFAULTS = {
    "push_time": "09:00",
    "frequency": "daily",
    "enable_news": True,
    "enable_algorithm": True,
    "enable_framework": False,
    "opacity": 38,
    "default_state": "normal",
    "auto_start": True,
    "hotkey": True,
    # 默认不把窗口挂进 explorer 的桌面层：跨进程 SetParent 会让 DWM 丙稀酸材质
    # 在桌面重绘时失效（窗口还在但画不出内容）。改用 WindowStaysOnBottomHint，
    # 同样做到"壁纸之上、应用窗口之下"，但由本进程自己管理 Z 序，稳定得多。
    "pin_desktop": False,
    "last_monitor": "",
    "algo_seq": 0,
    "framework_seq": 0,
    "pause_date": "",
}


def _path():
    os.makedirs(APP_DIR, exist_ok=True)
    return os.path.join(APP_DIR, "config.json")


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self.load()

    def load(self):
        p = _path()
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self._data.update(json.load(f))
            except (OSError, ValueError):
                pass

    def save(self):
        p = _path()
        tmp = p + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, p)
            return True
        except OSError:
            return False

    def get(self, key, default=None):
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value, autosave=True):
        if self._data.get(key) == value:
            return
        self._data[key] = value
        if autosave:
            self.save()

    def enabled_types(self):
        types = []
        if self.get("enable_news"):
            types.append("news")
        if self.get("enable_algorithm"):
            types.append("algorithm")
        if self.get("enable_framework"):
            types.append("framework")
        return types or ["algorithm"]
