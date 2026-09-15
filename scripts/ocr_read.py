#!/usr/bin/python3
"""截图 OCR 文字读取脚本。

调用 sn-image-ocr 技能的 ocr.py，支持：
- 全屏截图 + OCR
- 指定窗口截图 + OCR
- 指定区域截图 + OCR
- 输出 JSON（含文字、坐标、置信度）或纯文本

用法:
    ocr_read.py [选项]
    ocr_read.py --app ZCode                    # 截指定应用窗口并 OCR
    ocr_read.py --window <WID>                 # 截指定窗口 ID 并 OCR
    ocr_read.py --region 0,0,800,600           # 截区域并 OCR
    ocr_read.py --dump /tmp/out.png            # 只截图不 OCR（调试用）
    ocr_read.py --json                         # JSON 输出（默认）
    ocr_read.py --text                         # 纯文本输出
    ocr_read.py --prompt "提取所有文字"         # 自定义提示词
    ocr_read.py --crop 200,300,400,200         # 区域裁剪后 OCR
    ocr_read.py --threshold 0.6                # 置信度阈值
    ocr_read.py --timeout 30                   # 整体超时（秒）
"""
import os
import subprocess
import sys
import json
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env  # noqa: E402


OCR_PY = os.path.expanduser("~/.cc-switch/skills/sn-image-ocr/scripts/ocr.py")
PYTHON = "/home/sxkiss/bt/.venv/bin/python3"


def load_env():
    env_lines = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "env.py")],
        capture_output=True, text=True,
    ).stdout
    for line in env_lines.splitlines():
        if line.startswith("export "):
            k, v = line[7:].split("=", 1)
            os.environ[k] = v


def take_screenshot(path, args):
    """截屏到 path，返回 True 成功。"""
    cmd = [PYTHON, os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshot.py"), path]
    if args.app:
        cmd.extend(["--app", args.app])
    elif args.window:
        cmd.extend(["--window", args.window])
    elif args.region or args.crop:
        region = args.region or args.crop
        cmd.extend(["--region", region])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
    return os.path.exists(path) and r.returncode == 0


def run_ocr(img_path, prompt, threshold):
    """调用 sn-image-ocr 执行 OCR，返回 (json_data, elapsed_ms)。"""
    cmd = [PYTHON, OCR_PY, img_path, "--json", "--threshold", str(threshold)]
    if prompt:
        cmd += ["--prompt", prompt]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"OCR 失败: {r.stderr.strip()}", file=sys.stderr)
        return [], 0
    try:
        data = json.loads(r.stdout)
        elapsed = data[0]["elapsed_ms"] if data else 0
        return data, elapsed
    except json.JSONDecodeError:
        print(f"OCR 解析失败: {r.stdout[:200]}", file=sys.stderr)
        return [], 0


def main():
    parser = argparse.ArgumentParser(description="截图 + OCR 读取界面文字")
    parser.add_argument("--app", help="应用名（如 ZCode）")
    parser.add_argument("--window", help="窗口 WID")
    parser.add_argument("--region", help="截图区域 X,Y,W,H")
    parser.add_argument("--crop", dest="crop", help="同 --region")
    parser.add_argument("--dump", help="只截图，保存到此路径，不 OCR")
    parser.add_argument("--json", action="store_true", default=True, help="JSON 输出（默认）")
    parser.add_argument("--text", action="store_true", help="纯文本输出")
    parser.add_argument("--prompt", help="自定义 OCR 提示词")
    parser.add_argument("--threshold", type=float, default=0.5, help="置信度阈值（默认 0.5）")
    parser.add_argument("--timeout", type=int, default=30, help="截图超时秒数（默认 30）")
    args = parser.parse_args()
    load_env()

    # 先截图
    tmp_png = "/tmp/gui_ocr_temp.png"
    ok = take_screenshot(tmp_png, args)
    if not ok:
        print("截图失败", file=sys.stderr)
        sys.exit(1)

    # 只 dump 不 OCR
    if args.dump:
        os.replace(tmp_png, args.dump)
        print(f"截图已保存: {args.dump}")
        sys.exit(0)

    # OCR
    if not os.path.exists(OCR_PY):
        print(f"ERROR: sn-image-ocr 技能未安装: {OCR_PY}", file=sys.stderr)
        sys.exit(1)

    start = time.perf_counter()
    data, elapsed = run_ocr(tmp_png, args.prompt, args.threshold)
    total_ms = int((time.perf_counter() - start) * 1000)

    if not data:
        print("OCR 返回空结果", file=sys.stderr)
        sys.exit(1)

    # 输出
    if args.text:
        lines = []
        for entry in data:
            texts = [line["text"] for line in entry["lines"]]
            lines.append("\n".join(texts))
        print("\n".join(lines))
    else:
        # JSON：加上总耗时
        result = data[0].copy() if data else {}
        result["total_ms"] = total_ms
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # 清理临时文件
    try:
        os.remove(tmp_png)
    except Exception:
        pass


if __name__ == "__main__":
    main()