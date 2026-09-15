#!/usr/bin/python3
"""提取用户图形会话的 DISPLAY/XAUTHORITY/DBUS 环境变量并打印（供 shell source 或脚本用）。"""
import os, subprocess, re, glob

def run(cmd):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
    except: return ""

# DISPLAY: 从 xfce4-session / Xorg / Xvfb 环境
display = ""
for pid in run("pgrep -x xfce4-session").split() or run("pgrep -x Xorg").split() or run("pgrep -x Xvfb").split():
    try:
        env = open(f"/proc/{pid}/environ", "rb").read().decode("utf-8", "ignore")
        for line in env.split("\0"):
            if line.startswith("DISPLAY="): display = line.split("=",1)[1]; break
    except: pass
    if display: break
# Xvfb 通常无 DISPLAY 环境变量，但进程 cmdline 有 -screen 参数；从 /tmp/.X11-unix 推断活动显示
if not display:
    import glob
    socks = glob.glob("/tmp/.X11-unix/X*")
    if socks:
        # 按数字升序取最小（:10 优先于 :1024/:1025 等 gdm 会话号）
        nums = sorted(int(p.rsplit("X", 1)[1]) for p in socks if p.rsplit("X", 1)[1].isdigit())
        if nums:
            display = ":" + str(nums[0])
if not display: display = ":0"

# 2. XAUTHORITY: 从 Xorg cmdline -auth 解析
xauth = ""
xorg = run("pgrep -x Xorg | head -1")
if xorg:
    try:
        cmd = open(f"/proc/{xorg}/cmdline","rb").read().decode("utf-8","ignore").replace("\0"," ")
        import re
        m = re.search(r"-auth\s+(\S+)", cmd)
        if m:
            cwd = os.readlink(f"/proc/{xorg}/cwd") or os.path.expanduser("~")
            xauth = os.path.realpath(os.path.join(cwd, m.group(1)))
    except: pass
if not xauth: xauth = os.path.expanduser("~/.Xauthority")

# 3. DBUS: 用户 session bus
dbus = f"unix:path=/run/user/{os.getuid()}/bus"
xdg = f"/run/user/{os.getuid()}"

print(f"export DISPLAY={display or ':0'}")
print(f"export XAUTHORITY={xauth}")
print(f"export DBUS_SESSION_BUS_ADDRESS={dbus}")
print(f"export XDG_RUNTIME_DIR={xdg}")
