# -*- coding: utf-8 -*-
"""Win32 接口封装 —— 毛玻璃、桌面钉入、DPI、点击穿透、开机自启、全局热键。
仅依赖 ctypes + 标准库，不引入 pywin32。"""
import ctypes
import os
import subprocess
import sys
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

HWND = wintypes.HWND
BOOL = wintypes.BOOL
LPARAM = wintypes.LPARAM

# 64 位下 ctypes 默认按 32 位 c_int 处理返回值与整型实参，
# HRGN / HDC 等句柄会被截断成非法值，轻则调用失败、重则访问违规。
# 以下逐个声明真实签名，杜绝句柄截断。
_CINT = ctypes.c_int
_CUINT = ctypes.c_uint
_HANDLE = ctypes.c_void_p
_PTR = ctypes.c_ssize_t

user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = HWND
user32.FindWindowExW.argtypes = [HWND, HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = HWND
user32.SendMessageTimeoutW.argtypes = [HWND, _CUINT, ctypes.c_size_t, _PTR,
                                       _CUINT, _CUINT, ctypes.POINTER(wintypes.DWORD)]
user32.SendMessageTimeoutW.restype = _PTR
user32.SetParent.argtypes = [HWND, HWND]
user32.SetParent.restype = HWND
user32.ShowWindow.argtypes = [HWND, _CINT]
user32.ShowWindow.restype = BOOL
user32.SetWindowPos.argtypes = [HWND, HWND, _CINT, _CINT, _CINT, _CINT, _CUINT]
user32.SetWindowPos.restype = BOOL
user32.SetWindowRgn.argtypes = [HWND, _HANDLE, BOOL]
user32.SetWindowRgn.restype = _CINT
user32.IsWindowVisible.argtypes = [HWND]
user32.IsWindowVisible.restype = BOOL
user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = BOOL
user32.GetWindowLongPtrW.argtypes = [HWND, _CINT]
user32.GetWindowLongPtrW.restype = _PTR
user32.SetWindowLongPtrW.argtypes = [HWND, _CINT, _PTR]
user32.SetWindowLongPtrW.restype = _PTR
user32.GetAsyncKeyState.argtypes = [_CINT]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetDC.argtypes = [HWND]
user32.GetDC.restype = _HANDLE
user32.ReleaseDC.argtypes = [HWND, _HANDLE]
user32.ReleaseDC.restype = _CINT
user32.GetSystemMetrics.argtypes = [_CINT]
user32.GetSystemMetrics.restype = _CINT
if hasattr(user32, "GetDpiForWindow"):  # Win10 1607 之前无此 API
    user32.GetDpiForWindow.argtypes = [HWND]
    user32.GetDpiForWindow.restype = _CUINT

gdi32.CreateRoundRectRgn.argtypes = [_CINT, _CINT, _CINT, _CINT, _CINT, _CINT]
gdi32.CreateRoundRectRgn.restype = _HANDLE
gdi32.GetDeviceCaps.argtypes = [_HANDLE, _CINT]
gdi32.GetDeviceCaps.restype = _CINT

# ---------- 窗口合成（毛玻璃） ----------
ACCENT_DISABLED = 0
ACCENT_ENABLE_GRADIENT = 1
ACCENT_ENABLE_TRANSPARENTGRADIENT = 2
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_DEFAULT = 0
DWMWCP_DONOTROUND = 1
DWMWCP_ROUND = 2


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(ACCENT_POLICY)),
        ("SizeOfData", ctypes.c_size_t),
    ]


_SetWindowCompositionAttribute = user32.SetWindowCompositionAttribute
_SetWindowCompositionAttribute.argtypes = [HWND, ctypes.POINTER(WINCOMPATTRDATA)]
_SetWindowCompositionAttribute.restype = ctypes.c_int

_DwmSetWindowAttribute = ctypes.WinDLL("dwmapi").DwmSetWindowAttribute
_DwmSetWindowAttribute.argtypes = [HWND, ctypes.c_uint, ctypes.POINTER(ctypes.c_int), ctypes.c_uint]
_DwmSetWindowAttribute.restype = ctypes.c_int


def hwnd_of(widget) -> int:
    return int(widget.winId())


def _abgr(rgb, percent: int) -> int:
    """GradientColor 采用 AABBGGRR 字节序。"""
    r, g, b = rgb
    a = max(0, min(255, int(255 * percent / 100.0)))
    return (a << 24) | (b << 16) | (g << 8) | r


def set_glass(hwnd: int, rgb, percent: int) -> bool:
    """启用 DWM 丙稀酸毛玻璃。成功返回 True；失败返回 False（调用方需降级）。"""
    for state in (ACCENT_ENABLE_ACRYLICBLURBEHIND, ACCENT_ENABLE_BLURBEHIND):
        policy = ACCENT_POLICY()
        policy.AccentState = state
        policy.AccentFlags = 2 if state == ACCENT_ENABLE_ACRYLICBLURBEHIND else 0
        policy.GradientColor = _abgr(rgb, percent)
        data = WINCOMPATTRDATA()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.pointer(policy)
        data.SizeOfData = ctypes.sizeof(policy)
        try:
            if _SetWindowCompositionAttribute(HWND(hwnd), ctypes.byref(data)):
                return True
        except OSError:
            break
    return False


def disable_glass(hwnd: int) -> None:
    policy = ACCENT_POLICY()
    policy.AccentState = ACCENT_DISABLED
    data = WINCOMPATTRDATA()
    data.Attribute = 19
    data.Data = ctypes.pointer(policy)
    data.SizeOfData = ctypes.sizeof(policy)
    try:
        _SetWindowCompositionAttribute(HWND(hwnd), ctypes.byref(data))
    except OSError:
        pass


def set_corner_preference(hwnd: int, rounded: bool = True) -> None:
    val = ctypes.c_int(DWMWCP_ROUND if rounded else DWMWCP_DONOTROUND)
    try:
        _DwmSetWindowAttribute(HWND(hwnd), DWMWA_WINDOW_CORNER_PREFERENCE,
                               ctypes.byref(val), ctypes.sizeof(val))
    except OSError:
        pass


def set_rounded_region(hwnd: int, w: int, h: int, radius: int) -> None:
    """裁剪窗口为圆角矩形，使毛玻璃材质跟随圆角（Win10 无系统圆角时的必需手段）。"""
    rgn = gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, radius * 2, radius * 2)
    if rgn:
        user32.SetWindowRgn(HWND(hwnd), rgn, True)


# ---------- 钉入桌面层 ----------
_WNDENUMPROC = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)


SW_SHOW = 5


def pin_to_desktop(hwnd: int) -> str:
    """将窗口挂到桌面层，使其位于壁纸之上、其他应用窗口之下。

    返回生效的策略名；返回空串表示全部失败，调用方需降级。
    策略 1 workerw-sibling：Win10 经典形态，DefView 挂在某个 WorkerW 下，取其兄弟 WorkerW。
    策略 2 progman：Win11 常见形态，DefView 直接挂在 Progman 下，则挂到 Progman。
    """
    progman = user32.FindWindowW("Progman", None)
    if progman:
        result = wintypes.DWORD()
        user32.SendMessageTimeoutW(HWND(progman), 0x052C, 0, 0, 0, 1000, ctypes.byref(result))

    cands = []

    def _cb(h, _l):
        shell = user32.FindWindowExW(HWND(h), HWND(0), "SHELLDLL_DefView", None)
        if not shell:
            return True
        sibling = user32.FindWindowExW(HWND(0), HWND(h), "WorkerW", None)
        if sibling:
            cands.append(("workerw-sibling", sibling))
        cands.append(("progman", h))
        return False

    user32.EnumWindows(_WNDENUMPROC(_cb), 0)

    for name, target in cands:
        if target and user32.SetParent(HWND(hwnd), HWND(target)):
            user32.ShowWindow(HWND(hwnd), SW_SHOW)
            return name
    return ""


HWND_TOP = 0


def bring_top(hwnd: int) -> None:
    """在所属父窗口的兄弟序列内置顶：桌面图层内位于图标之上，仍低于应用窗口。"""
    user32.SetWindowPos(HWND(hwnd), HWND(HWND_TOP), 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def unpin(hwnd: int) -> bool:
    """撤销钉入：把窗口交回桌面顶层窗口序列，恢复为独立浮窗。"""
    return bool(user32.SetParent(HWND(hwnd), HWND(0)))


def is_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(HWND(hwnd)))


def window_rect(hwnd: int):
    """返回 (x, y, w, h)；用于核对窗口是否被放到屏幕外或尺寸异常。"""
    r = wintypes.RECT()
    if not user32.GetWindowRect(HWND(hwnd), ctypes.byref(r)):
        return None
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)


HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010


def keep_bottom(hwnd: int) -> None:
    """钉桌面失败时的降级：置于 Z 序底部，需由调用方定时维持。"""
    user32.SetWindowPos(HWND(hwnd), HWND(HWND_BOTTOM), 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


# ---------- DPI ----------
def dpi_scale(hwnd: int) -> float:
    try:
        dpi = user32.GetDpiForWindow(HWND(hwnd))
    except (AttributeError, OSError):
        dpi = 0
    if not dpi:
        dc = user32.GetDC(HWND(0))
        dpi = gdi32.GetDeviceCaps(dc, 88) if dc else 96
        if dc:
            user32.ReleaseDC(HWND(0), dc)
    return (dpi or 96) / 96.0


# ---------- 点击穿透 ----------
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020


def set_click_through(hwnd: int, enabled: bool) -> None:
    style = user32.GetWindowLongPtrW(HWND(hwnd), GWL_EXSTYLE)
    if enabled:
        style |= WS_EX_TRANSPARENT
    else:
        style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongPtrW(HWND(hwnd), GWL_EXSTYLE, style)


# ---------- 全局热键（Win+Shift+D） ----------
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_D = 0x44


def _key_down(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def hotkey_combo_down() -> bool:
    """轮询式检测 Win+Shift+D（Qt 原生事件过滤在各版本间差异较大，轮询更稳）。"""
    win = _key_down(VK_LWIN) or _key_down(VK_RWIN)
    return win and _key_down(VK_SHIFT) and _key_down(VK_D)


# ---------- 开机自启 ----------
TASK_NAME = "TodayFrontier"


def _startup_command() -> str:
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        exe = exe[:-10] + "pythonw.exe"
        if not os.path.exists(exe):
            exe = sys.executable
    main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "main.py")
    return '"%s" "%s"' % (exe, main_py)


def autostart_enabled() -> bool:
    try:
        # 中文 Windows 下 schtasks 输出为 GBK，必须明确编码并容错，
        # 否则 locale 解码失败会抛 UnicodeDecodeError
        r = subprocess.run(["schtasks", "/query", "/tn", TASK_NAME],
                           capture_output=True, text=True,
                           encoding="gbk", errors="replace", timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    """使用任务计划程序而非 Run 注册表项，避免触发 UAC 提示。"""
    try:
        if enabled:
            cmd = ["schtasks", "/create", "/tn", TASK_NAME, "/sc", "onlogon",
                   "/tr", _startup_command(), "/rl", "limited", "/f"]
        else:
            cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="gbk", errors="replace", timeout=20)
        return r.returncode == 0
    except Exception:
        return False


# ---------- 会话环境探测 ----------
SM_REMOTESESSION = 0x1000


def is_remote_session() -> bool:
    return bool(user32.GetSystemMetrics(SM_REMOTESESSION))
