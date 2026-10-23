# -*- coding: utf-8 -*-
"""主组件：三态（收起 / 默认 / 展开）与内容渲染 —— 对应需求文档第 6、7 章。"""
import webbrowser
from datetime import date

from PySide6.QtCore import Qt, QRect, QVariantAnimation, QEasingCurve, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu, QApplication

import theme
import win32_api
from widgets import GlassWindow, GlassCard, PanelRow, Chip, IconButton, label, elide

STATE_COLLAPSED = "collapsed"
STATE_NORMAL = "normal"
STATE_EXPANDED = "expanded"


class WidgetPanel(GlassWindow):
    refreshRequested = Signal()
    settingsRequested = Signal()
    opened = Signal(str)

    def __init__(self, cfg, parent=None):
        super().__init__(radius=theme.RADIUS_CONTAINER, parent=parent)
        self.cfg = cfg
        self.state = cfg.get("default_state") or STATE_NORMAL
        self.items = []
        self.hero_index = 0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(theme.DUR_STATE)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_geom)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(theme.PAD_CONTAINER, theme.PAD_CONTAINER,
                                     theme.PAD_CONTAINER, theme.PAD_CONTAINER)
        self.root.setSpacing(theme.GAP_MODULE)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    # ---------------- 数据 ----------------
    def set_items(self, items):
        self.items = items or []
        if self.items:
            self.hero_index = date.today().timetuple().tm_yday % len(self.items)

    def _item_of(self, kind):
        for i in self.items:
            if i.get("type") == kind:
                return i
        return None

    def _hero(self):
        if not self.items:
            return None
        return self.items[self.hero_index % len(self.items)]

    # ---------------- 状态与布局 ----------------
    def width_for_state(self):
        return theme.W_COLLAPSED if self.state == STATE_COLLAPSED else theme.W_NORMAL

    def target_rect(self):
        screen = QGuiApplication.primaryScreen()
        g = screen.availableGeometry()
        w = self.width_for_state()
        h = self._target_height
        return QRect(g.right() - w - theme.EDGE_RIGHT, g.top() + theme.EDGE_TOP, w, h)

    def relayout(self, animate=True):
        self._rebuild_layout()
        collapsed = self.state == STATE_COLLAPSED
        pad = 0 if collapsed else theme.PAD_CONTAINER
        self.root.setContentsMargins(pad, pad, pad, pad)
        if collapsed:
            self._build_collapsed()
        elif self.state == STATE_EXPANDED:
            self._build_expanded()
        else:
            self._build_normal()
        self.setFixedWidth(self.width_for_state())
        # Qt 布局对象在多次重建后聚合值会失真（sizeHint 塌缩为仅边距），
        # 本组件为固定纵向栈，直接按条目累加求高，结果稳定且与内容一致。
        lay = self.root
        n = lay.count()
        h = lay.contentsMargins().top() + lay.contentsMargins().bottom()
        if n > 1:
            h += lay.spacing() * (n - 1)
        for i in range(n):
            w = lay.itemAt(i).widget()
            if w is not None:
                h += w.sizeHint().height()
        h = max(h, theme.H_COLLAPSED)
        if self.state == STATE_EXPANDED:
            h = max(theme.H_MIN_EXPANDED, min(theme.H_MAX_EXPANDED, h))
        h = min(h, theme.H_MAX_EXPANDED if self.state == STATE_EXPANDED else 520)
        self._target_height = h
        self.setFixedHeight(h)
        win32_api.set_rounded_region(win32_api.hwnd_of(self), self.width(), h, self.radius)
        target = self.target_rect()
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self.geometry() if self.isVisible() else
                                     QRect(target.x() + 40, target.y(), target.width(), target.height()))
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self.setGeometry(target)

    def _on_geom(self, v):
        r = v if isinstance(v, QRect) else QRect(v)
        self.setGeometry(r)

    def _clear(self):
        while self.root.count():
            it = self.root.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def _rebuild_layout(self):
        """每次重建连同布局对象一起丢弃：复用的布局对象在多次增删后
        height-for-width 状态会失真（hasHeightForWidth 误报 False），导致窗口高度塌缩。"""
        self._clear()
        QWidget().setLayout(self.root)  # 旧布局转移到临时对象后随其销毁
        self.root = QVBoxLayout(self)
        self.root.setSpacing(theme.GAP_MODULE)

    def set_state(self, state, animate=True):
        self.state = state
        self.relayout(animate=animate)

    def toggle(self):
        self.set_state(STATE_NORMAL if self.state == STATE_COLLAPSED else STATE_COLLAPSED)

    # ---------------- 各状态构建 ----------------
    def _build_collapsed(self):
        pill = GlassCard(radius=22, clickable=True)
        pill.setFixedHeight(theme.H_COLLAPSED)
        pill.clicked.connect(lambda: self.set_state(STATE_NORMAL))
        lay = QHBoxLayout(pill)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(8)
        icon = IconButton("collapse", 16, theme.ACCENT)
        icon.clicked.connect(lambda: self.set_state(STATE_NORMAL))
        lay.addWidget(icon)
        lay.addWidget(label(elide("今日前沿 · %d 条更新" % len(self.items),
                                  theme.font(11), theme.W_COLLAPSED - 12 * 2 - 16 - 8), 11))
        lay.addStretch(1)
        self.root.addWidget(pill)

    def _build_header(self, title, right_extra=True):
        row = QHBoxLayout()
        row.setSpacing(8)
        left = QHBoxLayout()
        left.setSpacing(8)
        left.addWidget(label(title, 15, theme.TEXT_1, QFont.Weight.DemiBold))
        if self.state != STATE_EXPANDED:
            left.addWidget(label(self._date_text(), 11, theme.TEXT_3))
        row.addLayout(left)
        row.addStretch(1)
        if self.state == STATE_EXPANDED:
            row.addWidget(label("%d 条" % len(self.items), 11, theme.TEXT_3))
        if right_extra:
            gear = IconButton("gear", 18)
            gear.clicked.connect(self.open_settings)
            close = IconButton("close", 18)
            close.clicked.connect(lambda: self.set_state(STATE_COLLAPSED))
            row.addWidget(gear)
            row.addWidget(close)
        else:
            back = IconButton("close", 18)
            back.clicked.connect(lambda: self.set_state(STATE_NORMAL))
            row.addWidget(back)
        wrap = QWidget()
        wrap.setLayout(row)
        self.root.addWidget(wrap)

    def _date_text(self):
        d = date.today()
        week = "一二三四五六日"[d.weekday()]
        return "%d月%d日 周%s" % (d.month, d.day, week)

    def _build_normal(self):
        self._build_header("今日前沿")
        hero = self._hero()
        if hero:
            self.root.addWidget(self._hero_card(hero))
        else:
            self.root.addWidget(self._empty_card())
        for kind, icon_kind, color in (("algorithm", "algo", theme.TAG_ALGO),
                                      ("framework", "framework", theme.TAG_FRAMEWORK)):
            if kind == "algorithm" and not self.cfg.get("enable_algorithm"):
                continue
            if kind == "framework" and not self.cfg.get("enable_framework"):
                continue
            item = self._item_of(kind)
            if item:
                self.root.addWidget(self._mini_row(item, icon_kind, color))
        self.root.addWidget(self._footer())

    def _period(self, kind):
        base = self.cfg.get("algo_seq") if kind == "algorithm" else self.cfg.get("framework_seq")
        return int(base or 0) + 1

    def _chip_text(self, item):
        if item.get("type") == "algorithm":
            return "每日算法 · 第 %d 期" % self._period("algorithm")
        if item.get("type") == "framework":
            return "每日框架 · 第 %d 期" % self._period("framework")
        return "科技资讯"

    def _tag_color(self, kind):
        return {"algorithm": theme.TAG_ALGO,
                "framework": theme.TAG_FRAMEWORK}.get(kind, theme.TAG_NEWS)

    def _hero_card(self, item):
        card = GlassCard(radius=theme.RADIUS_CARD)
        card.clicked.connect(lambda: self._open(item))
        v = QVBoxLayout(card)
        v.setContentsMargins(theme.PAD_CARD, theme.PAD_CARD, theme.PAD_CARD, theme.PAD_CARD)
        v.setSpacing(theme.GAP_CARD)

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(Chip(self._chip_text(item), self._tag_color(item.get("type"))))
        top.addWidget(label("%s · %s" % (item.get("source_name", ""), self._age(item)),
                            10, theme.TEXT_3))
        top.addStretch(1)
        v.addLayout(top)

        t = label(item.get("title", ""), 14, theme.TEXT_1, QFont.Weight.DemiBold, wrap=True)
        t.setMaximumWidth(theme.W_NORMAL - 2 * theme.PAD_CONTAINER - 2 * theme.PAD_CARD)
        v.addWidget(t)
        s = label(item.get("summary", ""), 12, theme.TEXT_2, wrap=True)
        s.setMaximumWidth(theme.W_NORMAL - 2 * theme.PAD_CONTAINER - 2 * theme.PAD_CARD)
        v.addWidget(s)

        link = label("阅读全文", 11, theme.ACCENT, QFont.Weight.Medium)
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.mousePressEvent = lambda e: self._open(item)
        v.addWidget(link)
        return card

    def _empty_card(self):
        card = GlassCard(radius=theme.RADIUS_CARD, clickable=False)
        v = QVBoxLayout(card)
        v.setContentsMargins(theme.PAD_CARD, theme.PAD_CARD, theme.PAD_CARD, theme.PAD_CARD)
        v.addWidget(label("暂无新内容", 14, theme.TEXT_1, QFont.Weight.DemiBold))
        v.addWidget(label("请检查网络连接后点击底栏刷新按钮重试。", 12, theme.TEXT_2, wrap=True))
        return card

    def _mini_row(self, item, icon_kind, color):
        row = PanelRow(padding=12)
        icon = IconButton(icon_kind, 16, color)
        icon.clicked.connect(lambda: self._open(item))
        row.layout_.addWidget(icon)
        text = "今日%s · %s" % ("算法" if item.get("type") == "algorithm" else "框架",
                               item.get("title", ""))
        row.layout_.addWidget(label(elide(text, theme.font(12),
                                          theme.W_NORMAL - 2 * theme.PAD_CONTAINER - 24 - 60),
                                    12, theme.TEXT_1, QFont.Weight.Medium))
        row.layout_.addStretch(1)
        chev = IconButton("chevron", 14, theme.TEXT_3)
        row.layout_.addWidget(chev)
        row.clicked.connect(lambda: self._open(item))
        return row

    def _expanded_row(self, item):
        row = PanelRow(padding=10)
        kind = item.get("type")
        word = {"algorithm": "算法", "framework": "框架"}.get(kind, "资讯")
        row.layout_.addWidget(Chip(word, self._tag_color(kind)))
        row.layout_.addWidget(label(elide(item.get("title", ""), theme.font(12),
                                          theme.W_NORMAL - 2 * theme.PAD_CONTAINER - 24 - 60),
                                    12, theme.TEXT_1))
        row.clicked.connect(lambda: self._open(item))
        return row

    def _build_expanded(self):
        self._build_header("今日前沿 · 全部", right_extra=False)
        for item in self.items[:12]:
            self.root.addWidget(self._expanded_row(item))
        if not self.items:
            self.root.addWidget(self._empty_card())
        self.root.addStretch(1)

    def _footer(self):
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        updated = label("%s 已更新" % self.cfg.get("push_time"), 10, theme.TEXT_3)
        refresh = IconButton("refresh", 12)
        refresh.clicked.connect(lambda: self.refreshRequested.emit())
        row.addWidget(label(elide("数据源：Hacker News · arXiv · GitHub Trending",
                                  theme.font(10),
                                  theme.W_NORMAL - 2 * theme.PAD_CONTAINER - 12 - 6 * 2
                                  - updated.sizeHint().width() - 16), 10, theme.TEXT_3))
        row.addStretch(1)
        row.addWidget(refresh)
        row.addWidget(updated)
        return wrap

    def _age(self, item):
        return "今日"

    # ---------------- 动作 ----------------
    def _open(self, item):
        url = item.get("source_url")
        if url:
            webbrowser.open(url)
            self.opened.emit(item.get("id"))

    def _menu(self, pos):
        m = QMenu(self)
        m.addAction("立即刷新", lambda: self.refreshRequested.emit())
        m.addAction("设置", self.open_settings)
        m.addAction("收起" if self.state != STATE_COLLAPSED else "展开", self.toggle)
        m.addSeparator()
        m.addAction("退出", lambda: QApplication.quit())
        m.exec(self.mapToGlobal(pos))

    def open_settings(self):
        self.settingsRequested.emit()

    def wheelEvent(self, e):
        if not self.items:
            return
        delta = 1 if e.angleDelta().y() < 0 else -1
        if self.state == STATE_NORMAL:
            self.hero_index = (self.hero_index + delta) % len(self.items)
            self.relayout(animate=False)
        e.accept()
