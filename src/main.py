# -*- coding: utf-8 -*-
"""应用入口：装配主组件、设置面板、托盘、调度与系统能力。"""
import sys

sys.dont_write_bytecode = True

import ctypes
import importlib.util
import logging
import os
import re
import shutil
import subprocess
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                       "TodayFrontier", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
from logging.handlers import RotatingFileHandler

_log = logging.getLogger("TodayFrontier")
_log.setLevel(logging.INFO)
_handler = RotatingFileHandler(os.path.join(LOG_DIR, "app.log"),
                               maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_log.addHandler(_handler)
logging = _log

_TRACE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trace.log")


def _trace(msg):
    """逐步落盘到 trace.log，用于定位"进程活着但窗口不可见"这类问题。"""
    try:
        with open(_TRACE_PATH, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.now().strftime("%H:%M:%S"), msg))
    except Exception:
        pass


try:  # 原生崩溃（访问违规）不会走 sys.excepthook，只有 faulthandler 能留下栈
    import faulthandler

    _CRASH_LOG = os.path.join(LOG_DIR, "crash.log")
    _fh = open(_CRASH_LOG, "a", encoding="utf-8")
    _fh.write("\n===== %s =====\n" % datetime.now().isoformat(timespec="seconds"))
    faulthandler.enable(file=_fh, all_threads=True)
    _trace("faulthandler -> %s" % _CRASH_LOG)
except Exception as _e:
    _trace("faulthandler unavailable: %s" % _e)


def _msgbox(text, title="今日前沿"):
    """无控制台时必须显式弹窗，否则失败对用户而言完全不可见。"""
    try:
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x00000010)  # MB_ICONERROR
    except Exception:
        pass


def _candidate_interpreters():
    """收集可能装有 PySide6 的候选解释器，不含任何本机绝对路径。

    优先级：项目虚拟环境 → Windows Python 启动器枚举的全部安装
    → PATH 上的 pythonw → 与当前解释器同级的 pythonw。
    """
    found = []
    seen = set()

    def add(path):
        if not path or not os.path.exists(path):
            return
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    # 1) 项目自带的虚拟环境
    for sub in (".venv", "venv", "env"):
        add(os.path.join(HERE, sub, "Scripts", "pythonw.exe"))

    # 2) py launcher 枚举的已注册 Python（-0p 打印版本号 + 安装路径）
    py = shutil.which("py")
    if py:
        try:
            out = subprocess.run([py, "-0p"], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=15)
            for line in (out.stdout or "").splitlines():
                for m in re.finditer(r"[A-Za-z]:\\\S*python\.exe", line):
                    exe = m.group(0)
                    add(os.path.join(os.path.dirname(exe), "pythonw.exe"))
                    add(exe)
        except Exception:
            pass

    # 3) PATH 上的 pythonw / python
    for name in ("pythonw", "python"):
        p = shutil.which(name)
        if p:
            add(p)

    # 4) 与当前解释器同级
    add(os.path.join(os.path.dirname(sys.executable), "pythonw.exe"))
    return found


def _relaunch_with_venv():
    """当前解释器缺 PySide6 时，自动切到装有依赖的解释器重跑。

    处理"直接双击 src\\main.py"这类场景：文件关联指向的可能是没装依赖的基础解释器，
    静默退出会让用户以为程序没反应。
    """
    if os.environ.get("TF_RELAUNCH") == "1":
        return False
    for exe in _candidate_interpreters():
        if os.path.abspath(exe) == os.path.abspath(sys.executable):
            continue
        try:
            r = subprocess.run([exe, "-c", "import PySide6"], timeout=90,
                               capture_output=True)
        except Exception:
            continue
        if r.returncode == 0:
            _trace("relaunch with %s" % exe)
            env = dict(os.environ)
            env["TF_RELAUNCH"] = "1"
            subprocess.Popen([exe, os.path.abspath(__file__)] + sys.argv[1:],
                             env=env, cwd=HERE)
            return True
    return False


def _install_crash_logging():
    """pythonw 无控制台：未捕获异常只会弹一个瞬间消失的错误框。
    必须在导入 PySide6 之前装好，否则依赖缺失这类导入期错误会静默丢失。"""
    import traceback

    if sys.stderr is None or sys.stdout is None:  # pythonw：标准流为空
        try:
            stream = open(os.path.join(LOG_DIR, "app.log"), "a", encoding="utf-8")
            if sys.stderr is None:
                sys.stderr = stream
            if sys.stdout is None:
                sys.stdout = stream
        except Exception:
            pass

    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            _trace("UNCAUGHT %s: %s" % (exc_type.__name__, exc))
        except Exception:
            pass
        logging.error("UNCAUGHT %s: %s\n%s", exc_type.__name__, exc, text)
        if sys.__stderr__:
            traceback.print_exception(exc_type, exc, tb, file=sys.__stderr__)
        _msgbox("程序出错，已记录到日志：\n%s\n\n%s: %s"
                % (os.path.join(LOG_DIR, "app.log"), exc_type.__name__, exc))

    sys.excepthook = hook


_install_crash_logging()
_trace("=== start === exe=%s" % sys.executable)

try:
    _has_qt = importlib.util.find_spec("PySide6") is not None
except Exception:
    _has_qt = False

if not _has_qt:
    _trace("PySide6 missing in %s" % sys.executable)
    if not _relaunch_with_venv():
        _msgbox("当前解释器未安装 PySide6：\n%s\n\n请双击项目根目录的 run.bat 启动。"
                % sys.executable)
    sys.exit(1)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

_trace("pyside6 imported")

import theme
import win32_api
import sources
import store
from config import Config, APP_DIR
from panel import WidgetPanel, STATE_NORMAL, STATE_COLLAPSED
from settings import SettingsPanel

_trace("modules imported")

def _tray_icon():
    pm = QPixmap(32, 32)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(theme.ACCENT))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, 28, 28)
    p.setPen(QColor(255, 255, 255))
    f = QFont(theme._FAMILY_CN, 13)
    f.setWeight(QFont.Weight.DemiBold)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "今")
    p.end()
    return QIcon(pm)


class App:
    def __init__(self):
        self.cfg = Config()
        self.items = store.load_items()
        self.panel = WidgetPanel(self.cfg)
        self.settings = None
        self.fetching = False
        self._hk_held = False
        self._pin_mode = ""
        self.last_push = None

        self.panel.refreshRequested.connect(self.refresh)
        self.panel.settingsRequested.connect(self.open_settings)
        self.panel.opened.connect(self._on_opened)

        self._build_tray()
        self._start_timers()
        _trace("app constructed")

    # ---------------- 数据 ----------------
    def today(self):
        day = date.today().isoformat()
        return [i for i in self.items if i.get("pushed_date") == day]

    def _library_picks(self):
        """每日各取一条算法 / 框架，序号仅在该类型当日缺失时递增。"""
        day = date.today().isoformat()
        have = {i.get("type") for i in self.items if i.get("pushed_date") == day}
        out = []
        for kind, seq_key, flag, short in (("algorithm", "algo_seq", "enable_algorithm", "algo"),
                                           ("framework", "framework_seq", "enable_framework", "fw")):
            if not self.cfg.get(flag) or kind in have:
                continue
            seq = int(self.cfg.get(seq_key) or 0)
            item = sources.pick_from_library(kind, seq)
            if not item:
                continue
            item["id"] = "%s-%s-%04d" % (day, short, seq + 1)
            out.append(item)
            self.cfg.set(seq_key, seq + 1)
        return out

    def refresh(self):
        if self.fetching:
            return
        self.fetching = True
        self.worker = sources.FetchWorker(self.cfg.enabled_types())
        self.worker.finished.connect(self._on_fetched)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_fetched(self, results):
        self.fetching = False
        self._merge(results or [])

    def _on_failed(self, msg):
        self.fetching = False
        logging.warning("fetch failed: %s", msg)
        self._merge([])

    def _merge(self, results):
        _trace("merge begin, fetched=%d" % len(results or []))
        day = date.today().isoformat()
        batch = []
        for idx, it in enumerate(results):
            it["id"] = "%s-%s-%03d" % (day, (it.get("type") or "news")[:3], idx)
            batch.append(it)
        batch += self._library_picks()
        added = store.add_batch(self.items, batch)
        if added:
            self.items.extend(added)
            self.items = store.prune(self.items)
            store.save_items(self.items)
        self.panel.set_items(self.today())
        _trace("merge set_items done, today=%d" % len(self.today()))
        if self.panel.isVisible():
            self.panel.relayout(animate=False)
        _trace("merge relayout done")
        self.last_push = day

    def _on_opened(self, item_id):
        store.mark_read(self.items, item_id)
        store.save_items(self.items)

    # ---------------- 设置面板 ----------------
    def open_settings(self):
        if self.settings is None:
            self.settings = SettingsPanel(self.cfg)
            self.settings.configChanged.connect(self._on_config_changed)
        self.settings.refresh()
        g = self.panel.geometry()
        self.settings.move(g.right() - self.settings.width(), g.top())
        self.settings.show()
        QTimer.singleShot(150, lambda: self._attach(self.settings))

    def _on_config_changed(self, key, value):
        if key == "opacity":
            self.panel.apply_glass(int(value))
            if self.settings is not None:
                self.settings.apply_glass(int(value))
        elif key in ("enable_news", "enable_algorithm", "enable_framework"):
            self.panel.set_items(self.today())
            self.panel.relayout(animate=False)
        elif key == "default_state":
            self.panel.set_state(value, animate=False)

    # ---------------- 窗口挂载 ----------------
    def start(self):
        self.panel.set_items(self.today())
        if not self.cfg.get("pin_desktop"):
            # 置底于普通窗口序列：位于壁纸之上、其他应用窗口之下，无需跨进程挂靠
            self.panel.setWindowFlags(self.panel.windowFlags()
                                      | Qt.WindowType.WindowStaysOnBottomHint)
        self.panel.set_state(self.cfg.get("default_state") or STATE_NORMAL, animate=False)
        # getRect() 返回 (x,y,w,h) 四元组，必须整体作为单个参数传入
        _trace("state set, target geom=%s" % (self.panel.geometry().getRect(),))
        self.panel.show()
        _trace("show() called")
        QTimer.singleShot(250, self._after_show)
        # 不在启动时静默创建计划任务；开关状态与系统真实状态对齐，
        # 仅当用户在设置面板切换时才创建 / 删除任务
        QTimer.singleShot(600, self._sync_autostart)
        if not self.today():
            QTimer.singleShot(1200, self.refresh)

    def _sync_autostart(self):
        """延后到首屏渲染之后执行：schtasks 查询为同步子进程，阻塞主线程会拖慢启动。"""
        try:
            real = win32_api.autostart_enabled()
        except Exception as e:
            logging.warning("autostart query failed: %s", e)
            return
        if real != bool(self.cfg.get("auto_start")):
            self.cfg.set("auto_start", real)

    def _after_show(self):
        # 顺序不可调换：DWM 丙稀酸对已挂到桌面层的子窗口会失效，须先开材质再钉桌面
        self._attach(self.panel)
        hwnd = win32_api.hwnd_of(self.panel)
        _trace("glass applied, rect=%s" % (win32_api.window_rect(hwnd),))

        if os.environ.get("TF_NOPIN") == "1" or not self.cfg.get("pin_desktop"):
            logging.info("floating mode: no desktop pinning")
            _trace("floating mode (bottom hint), pin skipped")
            self.panel.relayout(animate=False)
            self.panel.raise_()
            return

        self._pin_mode = win32_api.pin_to_desktop(hwnd)
        if self._pin_mode:
            logging.info("pinned to desktop via %s", self._pin_mode)
        else:
            logging.warning("pin_to_desktop failed, fallback to bottom Z-order")
            self._bottom_timer.start(2000)
        self.panel.relayout(animate=False)
        win32_api.bring_top(hwnd)

        # 钉入后必须复核可见性：SetParent 到 explorer 进程的窗口后，
        # 窗口有可能被父窗口裁剪或转入隐藏状态，此时撤销钉入改为普通浮窗。
        if not win32_api.is_visible(hwnd):
            logging.warning("invisible after pin, revert to floating window")
            _trace("INVISIBLE after pin -> revert")
            win32_api.unpin(hwnd)
            self.panel.show()
            self.panel.raise_()
            self.panel.relayout(animate=False)
        _trace("after pin: visible=%s rect=%s" % (win32_api.is_visible(hwnd),
                                                  win32_api.window_rect(hwnd)))

    def _attach(self, window):
        """应用毛玻璃；DWM 不可用时降级为自采桌面位图模糊。"""
        try:
            ok = window.apply_glass(int(self.cfg.get("opacity")))
        except Exception as exc:
            logging.warning("apply_glass error: %s", exc)
            ok = False
        if not ok:
            logging.info("glass fallback: self-blur")
            window.capture_selfblur()
        window.refresh_region()

    # ---------------- 定时与热键 ----------------
    def _start_timers(self):
        self._sched = QTimer(self.panel)
        self._sched.setInterval(30000)
        self._sched.timeout.connect(self._tick)
        self._sched.start()

        self._hk = QTimer(self.panel)
        self._hk.setInterval(120)
        self._hk.timeout.connect(self._poll_hotkey)
        self._hk.start()

        self._bottom_timer = QTimer(self.panel)
        self._bottom_timer.setInterval(2000)
        self._bottom_timer.timeout.connect(
            lambda: win32_api.keep_bottom(win32_api.hwnd_of(self.panel)))

        self._beat = 0
        self._hb = QTimer(self.panel)
        self._hb.setInterval(1000)
        self._hb.timeout.connect(self._heartbeat)
        self._hb.start()

    def _heartbeat(self):
        """启动后 15 秒逐秒记录窗口真实状态：区分"进程没起来"与"窗口不可见"。"""
        self._beat += 1
        hwnd = win32_api.hwnd_of(self.panel)
        _trace("beat %02d qt_visible=%s win_visible=%s rect=%s" % (
            self._beat, self.panel.isVisible(), win32_api.is_visible(hwnd),
            win32_api.window_rect(hwnd)))
        if self._beat >= 15:
            self._hb.stop()

    def _due_today(self):
        freq = self.cfg.get("frequency")
        if freq == "workday" and date.today().weekday() >= 5:
            return False
        if freq == "weekly" and date.today().weekday() != 0:
            return False
        return True

    def _tick(self):
        day = date.today().isoformat()
        if self.cfg.get("pause_date") == day or not self._due_today():
            return
        if self.last_push == day:
            return
        if datetime.now().strftime("%H:%M") >= str(self.cfg.get("push_time")):
            self.refresh()

    def _poll_hotkey(self):
        if not self.cfg.get("hotkey"):
            return
        if win32_api.hotkey_combo_down():
            if not self._hk_held:
                self._hk_held = True
                self.panel.toggle()
        else:
            self._hk_held = False

    # ---------------- 托盘 ----------------
    def _build_tray(self):
        self.tray = QSystemTrayIcon(_tray_icon())
        self.tray.setToolTip("今日前沿")
        menu = QMenu()
        self._menu = menu  # 持有引用：setContextMenu 不接管所有权
        menu.setStyleSheet("QMenu {background:#1C1E26;color:#fff;border-radius:8px;}"
                           "QMenu::item {padding:6px 20px;}"
                           "QMenu::item:selected {background:#2997FF;}")
        menu.addAction("立即刷新", self.refresh)
        menu.addAction("设置", self.open_settings)
        menu.addAction("收起 / 展开", self.panel.toggle)
        menu.addAction("暂停今日推送", self._pause_today)
        menu.addSeparator()
        menu.addAction("退出", QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.panel.toggle()

    def _pause_today(self):
        self.cfg.set("pause_date", date.today().isoformat())
        self.tray.showMessage("今日前沿", "今日推送已暂停，明日自动恢复。",
                              QSystemTrayIcon.MessageIcon.Information, 2000)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("TodayFrontier")

    import traceback

    def _on_quit():
        stack = traceback.extract_stack()[:-1]
        _trace("aboutToQuit, initiated from:\n  " + "\n  ".join(
            "%s:%d %s" % (f.filename, f.lineno, f.name) for f in stack[-10:]))

    app.aboutToQuit.connect(_on_quit)

    a = App()
    a.start()
    rc = app.exec()
    _trace("exec returned %d" % rc)
    sys.exit(rc)


if __name__ == "__main__":
    main()
