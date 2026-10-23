# -*- coding: utf-8 -*-
"""设计 Token —— 对应《需求规格说明书》第 5 章。所有视觉常量集中于此，禁止在业务代码中硬编码。"""
from PySide6.QtGui import QColor, QFont, QFontDatabase

# ---------- 色彩 ----------
ACCENT = QColor(0x29, 0x97, 0xFF)
TAG_NEWS = QColor(0x29, 0x97, 0xFF)
TAG_ALGO = QColor(0x30, 0xD1, 0x58)
TAG_FRAMEWORK = QColor(0xFF, 0x9F, 0x0A)

GLASS_RGB = (18, 20, 28)          # 玻璃底色 RGB
GLASS_STROKE = QColor(255, 255, 255, 56)    # rgba(255,255,255,0.22)
GLASS_HILITE = QColor(255, 255, 255, 46)    # rgba(255,255,255,0.18)
CARD_IDLE = QColor(255, 255, 255, 18)       # rgba(255,255,255,0.07)
CARD_HOVER = QColor(255, 255, 255, 31)      # rgba(255,255,255,0.12)
ROW_IDLE = QColor(255, 255, 255, 13)
DIVIDER = QColor(255, 255, 255, 20)
SHADOW = QColor(0, 0, 0, 89)                # rgba(0,0,0,0.35)

TEXT_1 = QColor(0xFF, 0xFF, 0xFF)
TEXT_2 = QColor(0xC9, 0xC9, 0xCE)
TEXT_3 = QColor(0x98, 0x98, 0x9D)

# ---------- 尺寸 ----------
W_NORMAL = 360
W_COLLAPSED = 196
H_COLLAPSED = 44
W_SETTINGS = 328

PAD_CONTAINER = 16
PAD_CARD = 12
GAP_MODULE = 12
GAP_CARD = 8
GAP_ROW = 10

RADIUS_CONTAINER = 24
RADIUS_CARD = 14
RADIUS_ROW = 12
RADIUS_CHIP = 999
RADIUS_SETTING_ROW = 12

EDGE_RIGHT = 24
EDGE_TOP = 24

H_MIN_EXPANDED = 280
H_MAX_EXPANDED = 480
H_MAX_SETTINGS = 620

# ---------- 动画（毫秒） ----------
DUR_PUSH_IN = 300
DUR_STATE = 200
DUR_HOVER = 120
DUR_PRESS = 80
EASE_PUSH = "cubic-bezier(0.32, 0.72, 0, 1)"

# ---------- 字体 ----------
_FAMILY_CN = "Noto Sans SC"
_FAMILY_NUM = "Inter"


def _resolve(preferred, fallbacks):
    # Qt6 中 QFontDatabase 的接口是静态的，实例化会拿到空字体列表
    families = set(QFontDatabase.families())
    for name in [preferred] + fallbacks:
        if name in families:
            return name
    return ""


_RESOLVED = False


def _init_families():
    global _FAMILY_CN, _FAMILY_NUM, _RESOLVED
    _FAMILY_CN = _resolve("Noto Sans SC", ["Microsoft YaHei", "微软雅黑"])
    _FAMILY_NUM = _resolve("Inter", ["Segoe UI", _FAMILY_CN])
    _RESOLVED = True


def font(size=12, weight=QFont.Weight.Normal, numeric=False):
    # 延迟到首次调用时解析，此时 QGuiApplication 已存在，字体列表才完整
    if not _RESOLVED:
        _init_families()
    f = QFont(_FAMILY_NUM if numeric else _FAMILY_CN, size)
    f.setWeight(weight)
    return f


def cn(size=12, weight=QFont.Weight.Normal):
    return font(size, weight, numeric=False)


def alpha_color(base_rgb, percent):
    """按透明度百分比生成带 alpha 的 QColor，用于玻璃填充。"""
    r, g, b = base_rgb
    return QColor(r, g, b, int(255 * percent / 100.0))
