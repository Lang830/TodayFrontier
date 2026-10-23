# -*- coding: utf-8 -*-
"""设置面板 —— 对应需求文档第 12 章。"""
from PySide6.QtCore import Qt, Signal, QTime
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget, QLabel,
                               QTimeEdit, QComboBox)

import theme
import win32_api
from widgets import GlassWindow, PanelRow, Toggle, OpacitySlider, label


def _dark_palette(w):
    """QSS 对原生子控件的文字色不总生效，直接改调色板兜底。"""
    pal = w.palette()
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText,
                 QPalette.ColorRole.WindowText):
        pal.setColor(role, QColor(255, 255, 255))
    pal.setColor(QPalette.ColorRole.Base, QColor(0x23, 0x25, 0x2E))
    pal.setColor(QPalette.ColorRole.Button, QColor(0x23, 0x25, 0x2E))
    pal.setColor(QPalette.ColorRole.Window, QColor(0x23, 0x25, 0x2E))
    w.setPalette(pal)

GROUPS = [
    ("推送", [
        ("time", "每日推送时间", "time"),
        ("frequency", "推送频率", "combo"),
    ]),
    ("内容偏好", [
        ("enable_news", "科技资讯", "toggle"),
        ("enable_algorithm", "每日算法", "toggle"),
        ("enable_framework", "每日框架", "toggle"),
    ]),
    ("外观", [
        ("opacity", "玻璃透明度", "slider"),
        ("default_state", "默认状态", "combo"),
    ]),
    ("系统", [
        ("auto_start", "开机自动启动", "toggle"),
        ("hotkey", "全局热键 Win+Shift+D", "toggle"),
    ]),
]

FREQ_ITEMS = [("每天 1 次", "daily"), ("工作日", "workday"), ("每周一", "weekly")]
STATE_ITEMS = [("默认态", "normal"), ("收起态", "collapsed")]


class SettingsPanel(GlassWindow):
    configChanged = Signal(str, object)

    def __init__(self, cfg, parent=None):
        super().__init__(radius=theme.RADIUS_CONTAINER, parent=parent)
        self.cfg = cfg
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(theme.PAD_CONTAINER, theme.PAD_CONTAINER,
                                     theme.PAD_CONTAINER, theme.PAD_CONTAINER)
        self.root.setSpacing(theme.GAP_MODULE)
        self._build()

    def _build(self):
        self._clear()
        head = QHBoxLayout()
        head.addWidget(label("设置", 15, theme.TEXT_1, QFont.Weight.DemiBold))
        head.addStretch(1)
        wrap = QWidget()
        wrap.setLayout(head)
        self.root.addWidget(wrap)

        for group, rows in GROUPS:
            self.root.addWidget(label(group, 11, theme.TEXT_3, QFont.Weight.Medium))
            for key, text, kind in rows:
                self.root.addWidget(self._row(key, text, kind))
        self.root.addStretch(1)
        self.root.addWidget(label("今日前沿 v0.1.0 · Windows 10 / 11", 10, theme.TEXT_3))

        self.setFixedWidth(theme.W_SETTINGS)
        lay = self.root
        n = lay.count()
        h = lay.contentsMargins().top() + lay.contentsMargins().bottom()
        if n > 1:
            h += lay.spacing() * (n - 1)
        for i in range(n):
            w = lay.itemAt(i).widget()
            if w is not None:
                h += w.sizeHint().height()
        h = max(200, min(h, theme.H_MAX_SETTINGS))
        self.setFixedHeight(h)
        win32_api.set_rounded_region(win32_api.hwnd_of(self), self.width(), h, self.radius)

    def _clear(self):
        while self.root.count():
            it = self.root.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    # ---------------- 行控件 ----------------
    def _row(self, key, text, kind):
        row = PanelRow(padding=12, interactive=False)
        row.layout_.addWidget(label(text, 12, theme.TEXT_1))
        row.layout_.addStretch(1)
        if kind == "toggle":
            tg = Toggle(bool(self.cfg.get(key)))
            tg.stateChanged.connect(lambda v, k=key: self._commit(k, v))
            row.layout_.addWidget(tg)
        elif kind == "slider":
            val = QLabel("%d%%" % int(self.cfg.get(key)))
            val.setFont(theme.font(12))
            val.setStyleSheet("color: %s; background: transparent;" % theme.ACCENT.name())
            sl = OpacitySlider(int(self.cfg.get(key)))
            sl.setFixedWidth(120)
            sl.valueChanged.connect(lambda v, lb=val: lb.setText("%d%%" % v))
            sl.sliderReleased.connect(lambda s=sl: self._commit("opacity", s.value()))
            row.layout_.addWidget(sl)
            row.layout_.addWidget(val)
        elif kind == "time":
            t = QTimeEdit()
            hh, mm = str(self.cfg.get("push_time")).split(":")
            t.setTime(QTime(int(hh), int(mm)))
            t.setDisplayFormat("HH:mm")
            t.setFixedWidth(70)
            t.setFixedHeight(24)
            t.setFixedWidth(84)
            # 仅隐藏上下调节按钮；不要对该控件设颜色类 QSS（会覆盖调色板导致文字变暗）
            t.setStyleSheet("QTimeEdit::up-button,QTimeEdit::down-button{width:0;}")
            _dark_palette(t)
            t.editingFinished.connect(lambda: self._commit("push_time", t.time().toString("HH:mm")))
            row.layout_.addWidget(t)
        elif kind == "combo":
            items = FREQ_ITEMS if key == "frequency" else STATE_ITEMS
            cb = QComboBox()
            for name, val in items:
                cb.addItem(name, val)
            cur = self.cfg.get("frequency") if key == "frequency" else self.cfg.get("default_state")
            idx = cb.findData(cur)
            if idx >= 0:
                cb.setCurrentIndex(idx)
            cb.setFixedWidth(100)
            cb.setFixedHeight(24)
            _dark_palette(cb)
            cb.currentIndexChanged.connect(
                lambda i, c=cb: self._commit("frequency" if key == "frequency" else "default_state",
                                             c.currentData()))
            row.layout_.addWidget(cb)
        return row

    def _commit(self, key, value):
        self.cfg.set(key, value)
        if key == "auto_start":
            win32_api.set_autostart(bool(value))
        self.configChanged.emit(key, value)

    def refresh(self):
        self._build()
