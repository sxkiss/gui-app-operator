#!/usr/bin/python3
"""GUI 截图工具：全屏 / 窗口 / 区域截图，输出 PNG。

用法:
    screenshot.py <输出.png>                  # 全屏
    screenshot.py <输出.png> --app <应用名>   # 截指定应用窗口
    screenshot.py <输出.png> --window <WID>   # 截指定窗口 ID
    screenshot.py <输出.png> --region X,Y,W,H # 截区域（像素坐标）
    screenshot.py <输出.png> --crop X,Y,W,H   # 同 --region

依赖: ImageMagick `import`（已装）或 Pillow。自动加载 env.py 的 DISPLAY。
"""
import os
import subprocess
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env  # noqa: E402


def load_env():
    """把 env.py 输出的 export 行注入 os.environ。"""
    env_lines = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "env.py")],
        capture_output=True, text=True,
    ).stdout
    for line in env_lines.splitlines():
        if line.startswith("export "):
            k, v = line[7:].split("=", 1)
            os.environ[k] = v


def find_window_id(app_name):
    """用 xdotool 按应用名找窗口 ID。"""
    try:
        out = subprocess.run(
            ["xdotool", "search", "--name", app_name],
            capture_output=True, text=True, timeout=5,
        ).stdout
        ids = [l.strip() for l in out.splitlines() if l.strip()]
        return ids[0] if ids else None
    except Exception:
        return None


def main():
    load_env()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    out = args[0]
    region = None
    window_id = None

    i = 1
    while i < len(args):
        if args[i] == "--region" or args[i] == "--crop":
            region = args[i + 1]
            i += 2
        elif args[i] == "--window":
            window_id = args[i + 1]
            i += 2
        else:
            i += 1

    cmd = ["import", "-window"]
    if window_id:
        cmd.append(window_id)
    elif region:
        cmd.append("root")
    else:
        cmd.append("root")

    if region:
        # import 的 crop 语法: WxH+X+Y
        parts = region.replace(",", " ").split()
        if len(parts) == 4:
            x, y, w, h = parts
            cmd.append("-crop")
            cmd.append(f"{w}x{h}+{x}+{y}")

    cmd.append(out)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and os.path.exists(out):
            print(f"截图已保存: {out}")
            sys.exit(0)
        print(f"import 失败: {r.stderr.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"截图异常: {e}", file=sys.stderr)

    # 兜底：Pillow ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        if region:
            parts = region.replace(",", ":").split(":")
            if len(parts) == 4:
                x, y, w, h = map(int, parts)
                img = img.crop((x, y, x + w, y + h))
        img.save(out)
        print(f"截图已保存 (Pillow): {out}")
    except Exception as e:
        print(f"Pillow 兜底也失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()