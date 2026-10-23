# 今日前沿 · TodayFrontier

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/PySide6-Essentials-41CD52?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-97C459)

> 一个常驻 Windows 桌面右上角的毛玻璃信息推送小组件

🪟 **毛玻璃浮层** — DWM 丙稀酸材质 + 真圆角，壁纸之上、应用窗口之下
📰 **每日三推** — 一条科技前沿 + 一个算法 + 一个框架，每条都带可回溯原文链接
🌐 **多数据源** — Hacker News / arXiv / GitHub Trending，任一源失败自动跳过、不影响展示
🎛️ **三态切换** — 收起胶囊 ↔ 默认卡片 ↔ 展开列表，点击 / 滚轮 / 右键菜单均可操作
🧠 **内置知识库** — 80 个算法 + 47 个框架，纯 JSON 追加即扩展，无需改代码
⚡ **无缝降级** — 无 DWM / 远程桌面 / 断网时自动切换背景贴图或展示最近缓存
🔧 **后台常驻** — 系统托盘、开机自启（计划任务）、`Win + Shift + D` 全局热键

---

## 快速开始

```bat
git clone https://github.com/Lang830/TodayFrontier.git
cd TodayFrontier

python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

run.bat
```

> 依赖只有 `PySide6-Essentials`（约 80 MB），完整版含 Qt 全量库没必要。
> `.venv` 必须建在**项目根目录** —— `run.bat` 按这个约定找解释器，不查注册表也无需改脚本。
> 国内建议走清华镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
> **不要双击 `src\main.py`** —— 会走文件关联的解释器。虽然代码会自动扫一遍装了依赖的那个再重启，但没必要绕这步。

**环境**：Windows 10 21H2+ / Windows 11 · Python 3.11+（验证于 3.13）

---

## 交互速查

| 操作 | 效果 |
| --- | --- |
| 单击胶囊 | 收起态 ↔ 默认态 |
| 单击卡片区 | 默认态 ↔ 展开态 |
| 单击「阅读原文」 | 浏览器打开原文链接 |
| 滚轮 | 默认态切卡 / 展开态滚列表 |
| 右键 | 刷新 / 设置 / 收起 / 退出 |
| `Win + Shift + D` | 收起态 ↔ 默认态（设置里可关） |

组件位于应用窗口**之下**，桌面被窗口铺满时看不到 —— 按 `Win + D` 回桌面。

---

## 目录结构

```
TodayFrontier/
├─ src/
│  ├─ main.py        入口：装配、调度、托盘、热键
│  ├─ panel.py       主组件：三态布局
│  ├─ settings.py    设置面板
│  ├─ widgets.py     自绘组件：玻璃容器、卡片、标签、图标
│  ├─ win32_api.py   Win32 接口：毛玻璃、DPI、自启、热键
│  ├─ sources.py     数据源接入 + 内置库轮换
│  ├─ store.py       内容缓存与去重
│  ├─ config.py      配置读写
│  └─ theme.py       设计 Token
├─ resources/        algorithms.json · frameworks.json
├─ requirements.txt
└─ run.bat
```

**运行时数据** `%LOCALAPPDATA%\TodayFrontier\`

```
config.json     配置
cache.json      内容缓存（保留 30 天）
logs/app.log    运行日志（2 MB × 3 滚动）
logs/crash.log  原生崩溃栈
```

---

## 扩展内容库

往 `resources/algorithms.json` / `frameworks.json` 里直接追加，不用碰代码：

```json
{
  "name": "算法名称",
  "tags": ["领域", "复杂度"],
  "summary": "原理摘要，60 字左右",
  "source_name": "Wikipedia",
  "url": "https://en.wikipedia.org/wiki/..."
}
```

每日按文件顺序轮换，轮完回到第一条。

## 配置项

写在 `%LOCALAPPDATA%\TodayFrontier\config.json`：

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `push_time` | `09:00` | 每日推送时刻 |
| `opacity` | `38` | 玻璃不透明度（%） |
| `default_state` | `normal` | 启动状态 |
| `auto_start` | `true` | 开机自启 |
| `hotkey` | `true` | 全局热键 |
| `pin_desktop` | `false` | 挂进 explorer 桌面层（见下） |

`pin_desktop` 之所以默认关闭：把窗口 `SetParent` 给 Progman 属于跨进程挂靠，DWM 丙稀酸材质会在桌面重绘时失效，表现为「组件闪一下就没了」。现在改用 `WindowStaysOnBottomHint`，视觉效果一致（仍在应用窗口之下）但由本进程自管 Z 序，稳定得多。想试回旧行為就置 `true`。

---

## 已知限制

1. **窗外投影未实现** —— Qt 窗口尺寸即视觉尺寸，画不到边界外，需求文档那套 `y+12 / blur 32` 投影没做。
2. **按下态是提亮不是缩放** —— 需求文档的 `scale 0.95` 改成了卡片底色瞬时提亮。
3. **热键用轮询**（120 ms 检测）而非 `RegisterHotKey` 原生消息 —— Qt 原生事件过滤跨版本差异太大，代价是极小的定时开销。
4. **GitHub Trending 没有官方 API**，走页面解析，网站改版需同步规则。
5. **arXiv 在代理 / MITM 环境下会失败**，证书校验不过时跳过该源并记日志，家庭网络正常。
6. **收起胶囊字号 11 px**（设计稿 13 px）—— Noto Sans SC 字宽大于 SF Pro，13 px 在 196 px 胶囊里会溢出。
7. **内置库规模低于目标**：算法 80 条、框架 47 条（文档要求 ≥200 / ≥120），结构已就绪，按需追加。
