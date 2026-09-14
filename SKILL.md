---
name: gui-app-operator
description: 通过 AT-SPI 可访问性树操作 Linux 图形界面应用（无需视觉/OCR）。枚举桌面应用、读取控件树（按钮/文本框/菜单）、点击按钮、输入文字、激活窗口。适用于 xrdp/Xorg 会话中的 Electron 等 GUI 应用（如 ZCode）。
---

# GUI App Operator — 无头操作图形界面

## 适用场景
- 用户在 xrdp/Xorg 远程桌面（DISPLAY=:10）能看到 GUI 应用窗口，但 agent 在无头 shell 需要**读取并点击**界面控件
- 不依赖视觉/OCR：通过 AT-SPI 可访问性树读控件
- 已验证：ZCode (Electron) 界面完整可读可点

## 前置条件
- 系统包：`python3-gi`、`gir1.2-atspi-2.0`、`at-spi2-core`（均已装）
- 必须用 **/usr/bin/python3**（venv 无 gi）
- Electron 应用若 at-spi 树为空，需以 `--force-renderer-accessibility` 重启
- 环境变量从用户图形会话继承（见 scripts/env.py）

## 使用步骤
1. `bash scripts/env.py` 导出正确 DISPLAY/XAUTHORITY/DBUS
2. `python3 scripts/atspi.py apps` — 列出桌面应用找目标
3. `python3 scripts/atspi.py tree <app名>` — 读控件树
4. `python3 scripts/atspi.py click <app名> <按钮名>` — 点击
5. `python3 scripts/atspi.py type <app名> <入口名> <文字>` — 输入
6. 需要时 `xdotool windowactivate <窗口ID>` 激活

## 踩坑记录
- xdotool 查不到窗口：缺 XAUTHORITY（从 Xorg cmdline 的 -auth 参数解析）
- at-spi 树空：应用未开无障碍 → 重启加 --force-renderer-accessibility
- gi import 失败：用 /usr/bin/python3 而非 venv python
- 窗口映射不稳：先 windowactivate --sync 再读树
