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
    """模糊匹配：label 是子串即命中；role 可选过滤。返回所有匹配节点。"""
    hits = []
    def rec(node):
        try: cnt = node.get_child_count()
        except: return
        for j in range(cnt):
            try:
                c = node.get_child_at_index(j)
                nm = c.get_name() or ""
                match_name = label.lower() in nm.lower()
                match_role = role is None or c.get_role_name() == role
                if match_name and match_role:
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
        if not hits:
            print(f"未找到: {sys.argv[3]}")
        elif len(hits) == 1:
            hits[0].get_action().do_action(0)
            print(f"已点击: {hits[0].get_name()[:60]}")
        else:
            # 多命中：尝试用第5参数指定序号（1-based），否则列出候选
            idx = int(sys.argv[5]) - 1 if len(sys.argv) > 5 and sys.argv[5].isdigit() else None
            if idx is not None and 0 <= idx < len(hits):
                hits[idx].get_action().do_action(0)
                print(f"已点击[{idx+1}]: {hits[idx].get_name()[:60]}")
            else:
                print(f"命中{len(hits)}个，未自动点击。用法: click <app> <label> [role] [index]")
                for i, h in enumerate(hits, 1):
                    print(f"  [{i}] {h.get_name()[:80]}")
    elif cmd == "type":
        import time
        app = find_app(sys.argv[2])
        hits = find(app, sys.argv[3])
        if hits:
            widget = hits[0]
            text = sys.argv[4]
            # 方法1: 尝试 insert_text（适用于支持 AT-SPI EditableText 的控件）
            try:
                widget.insert_text(0, text, 0)
                print(f"已通过 insert_text 输入: {text}")
            except Exception:
                pass
            else:
                if widget.get_character_count() > 0:
                    return
            # 方法2: 键盘事件逐字符输入（兼容所有可聚焦控件）
            try:
                # 先聚焦
                widget.get_component_iface().grab_focus()
                time.sleep(0.1)
                # 全选删除旧内容
                Atspi.generate_keyboard_event(0xffe3, None, Atspi.KeySynthType.PRESS)
                Atspi.generate_keyboard_event(0x61, None, Atspi.KeySynthType.PRESS)
                Atspi.generate_keyboard_event(0x61, None, Atspi.KeySynthType.RELEASE)
                Atspi.generate_keyboard_event(0xffe3, None, Atspi.KeySynthType.RELEASE)
                time.sleep(0.2)
                # 逐字符输入
                for ch in text:
                    Atspi.generate_keyboard_event(ord(ch), None, Atspi.KeySynthType.PRESS)
                    time.sleep(0.05)
                    Atspi.generate_keyboard_event(ord(ch), None, Atspi.KeySynthType.RELEASE)
                    time.sleep(0.05)
                print(f"已通过键盘事件输入: {text}")
            except Exception as e:
                print(f"输入失败: {e}")
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
