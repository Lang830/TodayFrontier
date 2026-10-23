# -*- coding: utf-8 -*-
"""自绘组件库 —— 玻璃容器、卡片、标签、行、开关、图标按钮。
全部使用 QPainter 绘制，保证圆角、材质与描边在不同 DPI 下一致。"""
from PySide6.QtCore import Qt, QRectF, QPointF, QSize, Signal, QVariantAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QFontMetrics
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSlider

import theme


def rounded_path(rect, radius):
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def elide(text, font_obj, width):
    fm = QFontMetrics(font_obj)
    return fm.elidedText(text, Qt.TextElideMode.ElideRight, width)


def css_color(color):
    return "rgba(%d,%d,%d,%d)" % (color.red(), color.green(), color.blue(), color.alpha())


def label(text, size=12, color=theme.TEXT_1, weight=None, numeric=False, wrap=False):
    lb = QLabel(text)
    lb.setFont(theme.font(size, weight or QFont.Weight.Normal, numeric))
    lb.setStyleSheet("color: %s; background: transparent;" % css_color(color))
    lb.setWordWrap(wrap)
    return lb


# ---------------- 图标 ----------------
def draw_icon(p, kind, rect, color):
    """线性风格图标，stroke-width 1.8，端点圆角。"""
    pen = QPen(color, 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx, cy = rect.center().x(), rect.center().y()
    r = rect.width() / 2.0
    if kind == "gear":
        p.drawEllipse(QPointF(cx, cy), r * 0.28, r * 0.28)
        for i in range(8):
            import math
            a = math.pi / 4 * i
            p.drawLine(QPointF(cx + math.cos(a) * r * 0.45, cy + math.sin(a) * r * 0.45),
                       QPointF(cx + math.cos(a) * r * 0.9, cy + math.sin(a) * r * 0.9))
    elif kind == "close":
        p.drawLine(QPointF(cx - r * 0.5, cy - r * 0.5), QPointF(cx + r * 0.5, cy + r * 0.5))
        p.drawLine(QPointF(cx + r * 0.5, cy - r * 0.5), QPointF(cx - r * 0.5, cy + r * 0.5))
    elif kind == "chevron":
        p.drawLine(QPointF(cx - r * 0.25, cy - r * 0.5), QPointF(cx + r * 0.3, cy))
        p.drawLine(QPointF(cx + r * 0.3, cy), QPointF(cx - r * 0.25, cy + r * 0.5))
    elif kind == "refresh":
        p.drawArc(QRectF(cx - r * 0.7, cy - r * 0.7, r * 1.4, r * 1.4), 45 * 16, 300 * 16)
        p.drawLine(QPointF(cx + r * 0.45, cy - r * 0.55), QPointF(cx + r * 0.75, cy - r * 0.2))
        p.drawLine(QPointF(cx + r * 0.75, cy - r * 0.2), QPointF(cx + r * 0.25, cy - r * 0.15))
    elif kind == "algo":
        p.setBrush(color)
        p.drawEllipse(QPointF(rect.left() + r * 0.45, rect.bottom() - r * 0.5), r * 0.24, r * 0.24)
        p.drawEllipse(QPointF(rect.right() - r * 0.45, rect.top() + r * 0.5), r * 0.24, r * 0.24)
        p.drawLine(QPointF(rect.left() + r * 0.6, rect.bottom() - r * 0.7),
                   QPointF(rect.right() - r * 0.6, rect.top() + r * 0.7))
    elif kind == "framework":
        import math
        pts = []
        for i in range(6):
            a = math.pi / 3 * i - math.pi / 2
            pts.append(QPointF(cx + math.cos(a) * r * 0.85, cy + math.sin(a) * r * 0.85))
        for i in range(6):
            p.drawLine(pts[i], pts[(i + 1) % 6])
        for i in (0, 2, 4):
            p.drawLine(pts[i], QPointF(cx, cy))
    elif kind == "collapse":
        p.drawLine(QPointF(rect.left() + r * 0.4, cy), QPointF(rect.right() - r * 0.4, cy))
        p.drawLine(QPointF(rect.left() + r * 0.4, cy), QPointF(rect.left() + r * 0.75, cy - r * 0.4))
        p.drawLine(QPointF(rect.left() + r * 0.4, cy), QPointF(rect.left() + r * 0.75, cy + r * 0.4))


class IconButton(QWidget):
    clicked = Signal()

    def __init__(self, kind, size=18, color=None, parent=None):
        super().__init__(parent)
        self.kind = kind
        self._base = color or theme.TEXT_3
        self._cur = QColor(self._base)
        self.setFixedSize(size, size)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(theme.DUR_HOVER)
        self._anim.valueChanged.connect(self._on_anim)

    def sizeHint(self):
        return QSize(self.width(), self.height())

    def enterEvent(self, e):
        self._run(self._base, QColor(255, 255, 255))
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._run(QColor(self._cur), self._base)
        super().leaveEvent(e)

    def _run(self, a, b):
        self._anim.stop()
        self._anim.setStartValue(QColor(a))
        self._anim.setEndValue(QColor(b))
        self._anim.start()

    def _on_anim(self, v):
        self._cur = QColor(v)
        self.update()

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        draw_icon(p, self.kind, QRectF(self.rect()).adjusted(2, 2, -2, -2), self._cur)


# ---------------- 玻璃容器（顶层窗口） ----------------
class GlassWindow(QWidget):
    """无边框透明窗口：DWM 毛玻璃优先，失败则降级为自采桌面位图模糊。"""

    def __init__(self, radius=theme.RADIUS_CONTAINER, parent=None):
        super().__init__(parent)
        self.radius = radius
        self._opacity = 38
        self._glass_ok = False
        self._bg = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    # ---- 材质 ----
    def apply_glass(self, percent):
        """返回 True 表示 DWM 毛玻璃已生效（此时不再自绘填充，由系统提供底色）。"""
        import win32_api
        self._opacity = percent
        hwnd = win32_api.hwnd_of(self)
        win32_api.set_corner_preference(hwnd, True)
        ok = False
        if not win32_api.is_remote_session():
            ok = win32_api.set_glass(hwnd, theme.GLASS_RGB, percent)
        self._glass_ok = ok
        self.update()
        return ok

    def set_selfblur_background(self, image):
        """降级方案：使用事先模糊好的桌面位图作为背景。"""
        self._bg = image
        self.update()

    def refresh_region(self):
        import win32_api
        win32_api.set_rounded_region(win32_api.hwnd_of(self), self.width(), self.height(), self.radius)

    def capture_selfblur(self):
        """降级方案：先隐藏自身抓取桌面位图，做降采样模糊后作为背景贴图。"""
        geo = self.geometry()
        w, h = max(1, geo.width()), max(1, geo.height())
        self.hide()
        QTimer.singleShot(150, lambda: self._do_capture(geo, w, h))

    def _do_capture(self, geo, w, h):
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        screen = self.screen() or QApplication.primaryScreen()
        # grabWindow 使用设备像素；geometry 是逻辑像素，需按 DPR 换算
        dpr = screen.devicePixelRatio() or 1.0
        shot = screen.grabWindow(0, int(geo.x() * dpr), int(geo.y() * dpr),
                                 int(w * dpr), int(h * dpr))
        img = shot.toImage()
        if not img.isNull():
            small = img.scaled(max(1, w // 8), max(1, h // 8),
                               Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
            img = small.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        self.set_selfblur_background(img)
        self.show()
        self.raise_()

    # ---- 绘制 ----
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = rounded_path(r, self.radius)
        p.setClipPath(path)

        if not self._glass_ok:
            if self._bg is not None and not self._bg.isNull():
                p.drawImage(self.rect(), self._bg)
            p.fillPath(path, theme.alpha_color(theme.GLASS_RGB, self._opacity))

        # 顶部内高光
        p.setPen(QPen(theme.GLASS_HILITE, 1))
        p.drawLine(QPointF(self.radius, 1.5), QPointF(self.width() - self.radius, 1.5))
        # 描边
        p.setPen(QPen(theme.GLASS_STROKE, 1))
        p.drawPath(path)


# ---------------- 玻璃卡片（可交互） ----------------
class GlassCard(QWidget):
    clicked = Signal()
    hovered = Signal(bool)

    def __init__(self, radius=theme.RADIUS_CARD, clickable=True, parent=None):
        super().__init__(parent)
        self.radius = radius
        self.clickable = clickable
        self._alpha = theme.CARD_IDLE.alpha()
        self._pressed = False
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(theme.DUR_HOVER)
        self._anim.valueChanged.connect(self._on_anim)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    def _to(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._alpha)
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_anim(self, v):
        self._alpha = int(v)
        self.update()

    def enterEvent(self, e):
        if self.clickable:
            self._to(theme.CARD_HOVER.alpha())
            self.hovered.emit(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.clickable:
            self._to(theme.CARD_IDLE.alpha())
            self._pressed = False
        self.hovered.emit(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True
        self._to(46)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        inside = self.rect().contains(e.position().toPoint())
        self._pressed = False
        self._to(theme.CARD_HOVER.alpha() if inside else theme.CARD_IDLE.alpha())
        if inside and self.clickable:
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = rounded_path(r, self.radius)
        p.fillPath(path, QColor(255, 255, 255, self._alpha))
        p.setPen(QPen(theme.GLASS_STROKE, 1))
        p.drawPath(path)


class LinkLabel(QLabel):
    """可点击的文字链接（实例级覆盖 mousePressEvent 在 PySide6 中不可靠，故用显式子类）。"""
    clicked = Signal()

    def __init__(self, text, size=11, color=None, parent=None):
        super().__init__(text, parent)
        self.setFont(theme.font(size, QFont.Weight.Medium))
        self.setStyleSheet("color: %s; background: transparent;" % css_color(color or theme.ACCENT))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


# ---------------- 标签胶囊 ----------------
class Chip(QWidget):
    def __init__(self, text, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.text = text
        fm = QFontMetrics(theme.font(10))
        self.setFixedSize(fm.horizontalAdvance(text) + 16, fm.height() + 8)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QColor(self.color)
        bg.setAlpha(46)
        p.fillPath(rounded_path(QRectF(self.rect()), self.height() / 2.0), bg)
        p.setPen(self.color)
        p.setFont(theme.font(10, QFont.Weight.Medium))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)


# ---------------- 通用行（列表项 / 设置行） ----------------
class PanelRow(GlassCard):
    def __init__(self, parent=None, padding=12, interactive=True):
        super().__init__(radius=theme.RADIUS_ROW, clickable=interactive, parent=parent)
        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(padding, padding, padding, padding)
        self.layout_.setSpacing(10)
        self._alpha = theme.ROW_IDLE.alpha() if not interactive else theme.CARD_IDLE.alpha()


# ---------------- 开关 ----------------
class Toggle(QWidget):
    stateChanged = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 18)
        self.checked = checked
        self._x = 16 if checked else 2
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, v):
        self._x = float(v)
        self.update()

    def setChecked(self, v, emit=False):
        self.checked = v
        self._anim.stop()
        self._anim.setStartValue(self._x)
        self._anim.setEndValue(16.0 if v else 2.0)
        self._anim.start()
        if emit:
            self.stateChanged.emit(v)

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.position().toPoint()):
            self.setChecked(not self.checked, emit=True)
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QColor(theme.ACCENT) if self.checked else QColor(255, 255, 255, 38)
        p.fillPath(rounded_path(QRectF(self.rect()), 9), track)
        p.setBrush(QColor(255, 255, 255))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(self._x, 2, 14, 14))


# ---------------- 滑杆 ----------------
class OpacitySlider(QSlider):
    def __init__(self, value=38, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(20, 70)
        self.setValue(value)
        self.setFixedHeight(16)
        self.setStyleSheet(
            "QSlider::groove:horizontal {height:4px;background:rgba(255,255,255,0.12);border-radius:2px;}"
            "QSlider::sub-page:horizontal {background:%s;border-radius:2px;}"
            "QSlider::add-page:horizontal {background:rgba(255,255,255,0.12);border-radius:2px;}"
            "QSlider::handle:horizontal {width:12px;height:12px;margin:-4px 0;"
            "border-radius:6px;background:#FFFFFF;}" % theme.ACCENT.name()
        )
