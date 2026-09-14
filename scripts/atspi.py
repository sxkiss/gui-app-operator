#!/usr/bin/python33
"""AT-SPI 可访问性树工具：列应用 / 读树 / 点击 / 输入。用法见下。"""
import sys, os, subprocess

# 加载图形会话环境
def load_env():
    out = subprocess.run(["python3", os.path.join(os.path.dirname(__file__), "env.py")],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("export "):
            k, v = line[7:].split("=", 1)
            os.environ[k] = v

load_env()
import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi

def find_app(name):
    desktop = Atspi.get_desktop(0)
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app.get_name() and name.lower() in app.get_name().lower():
            return app
    return None

def walk(n, depth=0, max_depth=8, only_named=False, out=None):
    try: cnt = n.get_child_count()
    except: return
    for j in range(cnt):
        try:
            c = n.get_child_at_index(j)
            nm = c.get_name()
            if not only_named or nm:
                out.append("  "*depth + f"[{c.get_role_name()}] {nm!r}")
            walk(c, depth+1, max_depth, only_named, out)
        except: pass

def find(n, label, role=None):
    hits = []
    def rec(node):
        try: cnt = node.get_child_count()
        except: return
        for j in range(cnt):
            try:
                c = node.get_child_at_index(j)
                if c.get_name() == label and (role is None or c.get_role_name() == role):
                    hits.append(c)
                rec(c)
            except: pass
    rec(n)
    return hits

def main():
    if len(sys.argv) < 2:
        print("用法: atspi.py apps | tree <app> | click <app> <label> [role] | type <app> <label> <text> | listall")
        return
    cmd = sys.argv[1]
    if cmd == "apps":
        d = Atspi.get_desktop(0)
        for i in range(d.get_child_count()):
            a = d.get_child_at_index(i)
            print(f"[{i}] {a.get_name()}")
    elif cmd == "tree":
        app = find_app(sys.argv[2])
        if not app: print("未找到应用"); return
        out = []; walk(app, only_named=True, out=out)
        print("\n".join(out) if out else "(空树 — 可能需 --force-renderer-accessibility 重启)")
    elif cmd == "click":
        app = find_app(sys.argv[2])
        role = sys.argv[4] if len(sys.argv) > 4 else None
        hits = find(app, sys.argv[3], role)
        if hits:
            hits[0].get_action().do_action(0)
            print(f"已点击: {sys.argv[3]}")
        else:
            print(f"未找到: {sys.argv[3]}")
    elif cmd == "type":
        app = find_app(sys.argv[2])
        hits = find(app, sys.argv[3])
        if hits:
            # 尝试 setTextContents（若支持）
            try:
                hits[0].query_text().set_text_contents(0, len(sys.argv[4]), sys.argv[4])
                print(f"已输入: {sys.argv[4]}")
            except:
                print("该控件不支持直接输入，需用 xdotool type")
        else:
            print(f"未找到: {sys.argv[3]}")
    elif cmd == "listall":
        d = Atspi.get_desktop(0)
        for i in range(d.get_child_count()):
            a = d.get_child_at_index(i)
            out = []; walk(a, only_named=True, out=out)
            if out: print(f"--- {a.get_name()} ---\n" + "\n".join(out[:40]))

if __name__ == "__main__":
    main()
