---
name: gui-app-operator
description: "通过 AT-SPI 可访问性树操作 Linux 图形界面应用（主方案）；截图+OCR 为辅助方案（Electron 无障碍 API 受限或需要快速读取文字时使用）。枚举桌面应用、读取控件树、点击按钮、输入文字、激活/关闭窗口。适用于 xrdp/Xorg 会话及 Xvfb 无头环境中的 Electron、Firefox 等 GUI 应用。触发词：操作桌面应用 / 点击按钮 / GUI自动化 / 截图识别 / OCR识别 / 界面文字 / xdotool / atspi"
---

# GUI App Operator — 桌面应用自动化

## 工作流程（按推荐顺序）

```
1. env.py          → 获取 DISPLAY/XAUTHORITY
2. ocr_read.py     → 截图 + OCR 读取界面文字（快速确认状态/查找目标）
3. atspi.py        → 通过 AT-SPI 操作控件（点击/输入/关闭）
   或 xdotool       → 直接鼠标/键盘操作（AT-SPI 不可用时兜底）
```

## 前置依赖

### 系统包
```bash
sudo apt install -y python3-gi gir1.2-atspi-2.0 at-spi2-core xdotool imagemagick
pip install rapidocr-onnxruntime   # sn-image-ocr 技能依赖（已在 venv 安装）
```

### 环境变量（自动加载）
```bash
source <skill_dir>/scripts/env.py   # 自动导出 DISPLAY / XAUTHORITY / DBUS / XDG
```

## 脚本速查

| 脚本 | 命令 | 说明 |
|------|------|------|
| **env.py** | `source scripts/env.py` | 导出环境变量（必须第一步） |
| **ocr_read.py** | `python3 scripts/ocr_read.py --app ZCode` | 截 ZCode 窗口并 OCR 返回文字 |
| **screenshot.py** | `python3 scripts/screenshot.py out.png --app ZCode` | 仅截图保存 |
| **atspi.py** | `python3 scripts/atspi.py apps` | 列出所有桌面应用 |
| **atspi.py** | `python3 scripts/atspi.py tree ZCode` | 读取控件树 |
| **atspi.py** | `python3 scripts/atspi.py click ZCode 新建任务` | 点击按钮 |
| **atspi.py** | `python3 scripts/atspi.py type ZCode 输入框 "中文内容"` | 输入文字 |
| **atspi.py** | `python3 scripts/atspi.py activate ZCode` | 激活窗口到前台 |
| **atspi.py** | `python3 scripts/atspi.py close ZCode` | 关闭窗口（链式降级） |
| **atspi.py** | `python3 scripts/atspi.py listall` | 列出所有应用控件树摘要 |

## ocr_read.py 详解

```bash
# 截指定应用窗口 + OCR（JSON，含坐标）
python3 scripts/ocr_read.py --app ZCode --json

# 截指定窗口 ID + OCR（纯文本）
python3 scripts/ocr_read.py --window 4194307 --text

# 截屏幕区域 X,Y,W,H
python3 scripts/ocr_read.py --region 0,0,1920,1080 --text

# 只截图不 OCR（调试）
python3 scripts/ocr_read.py --app ZCode --dump /tmp/win.png

# 自定义提示词（引导 OCR 提取特定内容）
python3 scripts/ocr_read.py --app ZCode --prompt "提取对话历史中的所有消息文字"

# 提高置信度阈值（减少误识别）
python3 scripts/ocr_read.py --app ZCode --threshold 0.7
```

输出 JSON 格式：
```json
{
  "file": "/tmp/gui_ocr_temp.png",
  "lines": [
    {"text": "你好！", "confidence": 0.99, "box": [x1, y1, x2, y2]},
    {"text": "有什么可以帮你的吗？", "confidence": 0.97, "box": [x1, y1, x2, y2]}
  ],
  "elapsed_ms": 1800,
  "total_ms": 3200
}
```
`box` 为 [x1,y1,x2,y2] 像素坐标，可用于后续 xdotool 定位点击。

## atspi.py 详解

### type 中文输入策略
`type` 对英文走键盘事件（可靠）；对中文自动切换剪贴板粘贴方案（键盘事件对 Chromium 等 Electron 应用不稳定）。

### close 链式降级
`close <app>` 按顺序尝试：菜单关闭 → 按钮关闭 → Alt+F4 → xdotool windowclose，每步后验证窗口是否消失。

### find 模糊匹配
`click` / `type` 支持模糊匹配控件名（大小写不敏感子串），多命中时可指定序号：
```bash
# 第2个匹配结果
python3 scripts/atspi.py click ZCode "提问" 1 2
```

## 典型操作示例

### 示例 1：读取 ZCode 当前对话
```bash
source scripts/env.py
python3 scripts/ocr_read.py --app ZCode --text
```

### 示例 2：在 ZCode 中创建新任务
```bash
source scripts/env.py
python3 scripts/atspi.py click ZCode "新建任务"
sleep 1
python3 scripts/atspi.py type ZCode "任务名" "向 ZCode 提问"
python3 scripts/atspi.py key ZCode Return
```

### 示例 3：截图定位后点击
```bash
# 先 OCR 找坐标
result=$(python3 scripts/ocr_read.py --app ZCode --json)
# 提取按钮坐标 center_x, center_y（需自行解析 JSON）
xdotool mousemove <center_x> <center_y> click 1
```

### 示例 4：等待 AI 回复完成
```bash
# OCR 检测关键词出现
for i in $(seq 1 10); do
  text=$(python3 scripts/ocr_read.py --app ZCode --text)
  if echo "$text" | grep -q "已完成\|已回复"; then
    echo "AI 已回复"; break
  fi
  sleep 3
done
```

## 踩坑记录

- **xdotool 找不到窗口**：先 `source scripts/env.py` 导出正确 DISPLAY/XAUTHORITY
- **at-spi 树为空**：应用需加 `--force-renderer-accessibility` 重启（Electron 默认不开无障碍）
- **gi import 失败**：使用 `/usr/bin/python3`（系统 python），不要用 venv 内 python
- **type 中文乱码**：Electron/Chromium 上 AT-SPI 键盘事件不稳定，改用剪贴板粘贴或 ocr_read 辅助定位
- **窗口激活失败**：xdotool SetInputFocus 偶发 BadMatch，用 `import` 全屏截图代替
- **Xvfb 下连接失败**：无 `-auth` 时自动 unset XAUTHORITY 重试（env.py 已处理）
- **OCR 坐标与 xdotool 对齐**：`ocr_read.py` 的 box 是原图坐标，`xdotool mousemove` 也需要原图坐标，确保使用同一张截图