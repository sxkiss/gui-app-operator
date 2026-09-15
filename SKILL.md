---
name: gui-app-operator
description: 通过 AT-SPI 可访问性树操作 Linux 图形界面应用（无需视觉/OCR）。枚举桌面应用、读取控件树（按钮/文本框/菜单）、点击按钮、输入文字、激活窗口。适用于 xrdp/Xorg 会话中的 Electron 等 GUI 应用。
---

# GUI App Operator — 无头操作图形界面

## 适用场景
- 用户在 xrdp/Xorg 远程桌面（DISPLAY=:10）能看到 GUI 应用窗口，但 agent 在无头 shell 需要**读取并点击**界面控件
- 不依赖视觉/OCR：通过 AT-SPI 可访问性树读控件
- 已验证：Electron 类应用、Firefox 等标准 X11 应用

## 前置依赖

### 系统包（apt）
```bash
# AT-SPI 无障碍支持
sudo apt install -y python3-gi gir1.2-atspi-2.0 at-spi2-core

# xdotool 窗口管理与键盘输入（必须）
sudo apt install -y xdotool

# python-xlib 兜底（XTest 键盘模拟 + SetInputFocus）
pip install python-xlib   # 或 apt install python3-xlib
```

### 环境变量
- `DISPLAY=:10`（xrdp 会话）
- `XAUTHORITY=/home/sxkiss/.Xauthority`（从 Xorg cmdline 解析）

## 使用步骤
1. `bash scripts/env.py` — 导出 DISPLAY/XAUTHORITY/DBUS
2. `python3 scripts/atspi.py apps` — 列出桌面应用找目标
3. `python3 scripts/atspi.py tree <app名>` — 读控件树
4. `python3 scripts/atspi.py click <app名> <按钮名>` — 点击
5. `python3 scripts/atspi.py type <app名> <入口名> <文字>` — 输入
6. `python3 scripts/atspi.py activate <app名>` — 激活窗口（聚焦到前台）
7. 键盘快捷键：`python3 scripts/atspi.py key <app名> ctrl+l` — 返回自动先激活窗口

## 命令速查

| 命令 | 说明 |
|------|------|
| `apps` | 列出所有桌面应用 |
| `tree <app>` | 输出 AT-SPI 控件树 |
| `click <app> <控件名>` | 点击指定控件 |
| `type <app> <入口名> <文字>` | 向文本框输入文字 |
| `activate <app>` | 激活窗口到前台 |
| `key <app> <键名>` | 发送按键（如 ctrl+l / Return） |

## 踩坑记录
- **xdotool 找不到窗口**：缺 XAUTHORITY → 用 env.py 导出
- **at-spi 树为空**：应用未开无障碍 → 重启加 `--force-renderer-accessibility`
- **gi import 失败**：必须用 `/usr/bin/python3`，不要用 venv 内的 python
- **窗口激活失败**：xdotool 不可用时 fallback 到 Xlib SetInputFocus
- **按键无响应**：窗口未激活时 XTest 输入丢失 → 先 `activate` 或 `key` 已内置激活
- **中文输入**：type 命令对非 ASCII 文字自动切剪贴板粘贴
