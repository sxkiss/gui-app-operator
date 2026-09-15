#!/usr/bin/python3
"""提取用户图形会话的 DISPLAY/XAUTHORITY/DBUS 环境变量并打印（供 shell source 或脚本用）。

探测优先级：
1. DISPLAY: 当前 shell 已有 → xfce4-session → Xorg → Xvfb 进程 environ
   → 兜底从 /tmp/.X11-unix 取最小显示号（:10 优先于 gdm 的 :1024/:1025）
2. XAUTHORITY: Xorg cmdline -auth → ~/.Xauthority
3. DBUS: /run/user/<uid>/bus
"""
import os
import subprocess
import re
import glob


def run(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def find_display_from_proc(procs):
    """从指定进程的 environ 里找 DISPLAY。"""
    for pid in procs:
        try:
            env = open(f"/proc/{pid}/environ", "rb").read().decode("utf-8", "ignore")
            for line in env.split("\0"):
                if line.startswith("DISPLAY="):
                    return line.split("=", 1)[1]
        except Exception:
            continue
    return ""


def find_display_from_sockets():
    """无进程线索时，从 /tmp/.X11-unix 推断活动显示号。"""
    socks = glob.glob("/tmp/.X11-unix/X*")
    nums = sorted(
        int(p.rsplit("X", 1)[1])
        for p in socks
        if p.rsplit("X", 1)[1].isdigit()
    )
    return ":" + str(nums[0]) if nums else ""


def find_xauthority():
    """从 Xorg cmdline -auth 解析 XAUTHORITY，失败回退 ~/.Xauthority。"""
    xorg = run("pgrep -x Xorg | head -1")
    if xorg:
        try:
            cmd = open(f"/proc/{xorg}/cmdline", "rb").read().decode("utf-8", "ignore").replace("\0", " ")
            m = re.search(r"-auth\s+(\S+)", cmd)
            if m:
                cwd = os.readlink(f"/proc/{xorg}/cwd") or os.path.expanduser("~")
                return os.path.realpath(os.path.join(cwd, m.group(1)))
        except Exception:
            pass
    return os.path.expanduser("~/.Xauthority")


def main():
    # 1. DISPLAY：优先已有环境变量
    display = os.environ.get("DISPLAY", "").strip()
    if not display:
        display = find_display_from_proc(
            run("pgrep -x xfce4-session").split()
            or run("pgrep -x Xorg").split()
            or run("pgrep -x Xvfb").split()
        )
    if not display:
        display = find_display_from_sockets()
    if not display:
        display = ":0"

    # 2. XAUTHORITY
    xauth = os.environ.get("XAUTHORITY", "").strip()
    if not xauth:
        xauth = find_xauthority()

    # 3. DBUS / XDG
    uid = os.getuid()
    dbus = f"unix:path=/run/user/{uid}/bus"
    xdg = f"/run/user/{uid}"

    print(f"export DISPLAY={display}")
    print(f"export XAUTHORITY={xauth}")
    print(f"export DBUS_SESSION_BUS_ADDRESS={dbus}")
    print(f"export XDG_RUNTIME_DIR={xdg}")


if __name__ == "__main__":
    main()