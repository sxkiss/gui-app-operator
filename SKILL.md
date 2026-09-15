---
name: gui-app-operator
description: 通过 AT-SPI 可访问性树操作 Linux 图形界面应用（无需视觉/OCR）。枚举桌面应用、读取控件树（按钮/文本框/菜单）、点击按钮、输入文字、激活/关闭窗口。适用于 xrdp/Xorg 会话及 Xvfb 无头环境中的 Electron 等 GUI 应用。
---

# GUI App Operator — 无头操作图形界面

## 适用场景
- 用户在 xrdp/Xorg 远程桌面（DISPLAY=:10）能看到 GUI 应用窗口，但 agent 在无头 shell 需要**读取并点击**界面控件
- 不依赖视觉/OCR：通过 AT-SPI 可访问性树读控件
- 已验证：Electron 类应用、Firefox/Chrome 等标准 X11 应用

## 前置依赖

### 系统包（apt）
```bash
# AT-SPI 无障碍支持
sudo apt install -y python3-gi gir1.2-atspi-2.0 at-spi2-core

# xdotool 窗口管理 + 键盘输入 + close 兜底（必须）
sudo apt install -y xdotool

# python-xlib 兜底（XTest 键盘模拟 + SetInputFocus）
pip install python-xlib   # 或 apt install python3-xlib
```

### 环境变量
- `DISPLAY=:99`（Xvfb）或 `:10`（xrdp 会话）
- `XAUTHORITY=/home/sxkiss/.Xauthority`（从 Xorg cmdline 解析；Xvfb 无 auth 时自动降级）

## 使用步骤
1. `bash scripts/env.py` — 导出 DISPLAY/XAUTHORITY/DBUS（自动适配 Xvfb）
2. `python3 scripts/atspi.py apps` — 列出桌面应用找目标
3. `python3 scripts/atspi.py tree <app名>` — 读控件树
4. `python3 scripts/atspi.py click <app名> <按钮名>` — 点击
5. `python3 scripts/atspi.py type <app名> <入口名> <文字>` — 输入
6. `python3 scripts/atspi.py activate <app名>` — 激活窗口（聚焦到前台）
7. 键盘快捷键：`python3 scripts/atspi.py key <app名> ctrl+l` — 返回自动先激活窗口
8. 关闭窗口：`python3 scripts/atspi.py close <app名>` — 链式降级自动关闭

## 命令速查

| 命令 | 说明 |
|------|------|
| `apps` | 列出所有桌面应用 |
| `tree <app>` | 输出 AT-SPI 控件树 |
| `click <app> <控件名>` | 点击指定控件 |
| `type <app> <入口名> <文字>` | 向文本框输入文字（非 ASCII 自动切剪贴板粘贴） |
| `activate <app>` | 激活窗口到前台 |
| `key <app> <键名>` | 发送按键（如 ctrl+l / Return，自动先激活） |
| `close <app>` | 关闭窗口，链式降级：菜单 → 按钮 → Alt+F4 → xdotool，每步轮询验证 |

## close 链式降级机制

`close` 按顺序尝试关闭，**每步后轮询验证窗口是否真消失**（5s 超时），失败自动降级：

```
菜单关闭 → 按钮关闭 → Alt+F4 → xdotool windowclose
```

- Chrome 等自定义渲染按钮 AT-SPI 点击偶发失效 → 自动落到 xdotool 兜底
- 全部失败输出警告，不误报"已关闭"

## 环境适配（Xvfb / 无认证显示）

- **Xvfb 识别**：`env.py` 扩展探测 Xvfb 进程；无 DISPLAY 时按数字升序取 `/tmp/.X11-unix` 最小显示号（`:10` 优先于 gdm 的 `:1024/:1025`）
- **无认证降级**：`atspi.py` 带 XAUTHORITY 连接失败时自动 `unset XAUTHORITY` 重试（适配 Xvfb 无 `-auth`）
- **连接自检**：`load_env()` 后自动执行 X 连接握手探测（unix socket，不依赖 Xlib）

## 踩坑记录
- **xdotool 找不到窗口**：缺 XAUTHORITY → 用 env.py 导出
- **at-spi 树为空**：应用未开无障碍 → 重启加 `--force-renderer-accessibility`
- **gi import 失败**：必须用 `/usr/bin/python3`，不要用 venv 内的 python
- **窗口激活失败**：xdotool 不可用时 fallback 到 Xlib SetInputFocus
- **按键无响应**：窗口未激活时 XTest 输入丢失 → 先 `activate` 或 `key` 已内置激活
- **中文输入**：type 命令对非 ASCII 文字自动切剪贴板粘贴
- **Chrome 按钮点击失效**：自定义渲染按钮 AT-SPI 偶发无效 → close 自动 xdotool 兜底
- **Xvfb 下连接失败**：无 `-auth` → 自动 unset XAUTHORITY 重试