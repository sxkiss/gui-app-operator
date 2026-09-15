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

def x_connectable(display=None):
    """探测 X 显示是否可连接（unix socket 握手）。返回 True/False。"""
    import socket
    d = display or os.environ.get("DISPLAY", ":0")
    if d.startswith(":"):
        num = d.split(":", 1)[1].split(".", 1)[0]
        path = f"/tmp/.X11-unix/X{num}"
    elif d.startswith("unix:"):
        path = d.split(":", 2)[2]
    else:
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(path)
        s.sendall(b"\x6c\x00\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00")  # 握手: 协议 11.0
        data = s.recv(8)
        s.close()
        return len(data) >= 8
    except Exception:
        return False

def _ensure_x_connection():
    """确保能连上 X：带 XAUTHORITY 失败时自动降级为无认证重试。
    适用场景：Xvfb / Xephyr 等无 -auth 的虚拟显示，auth 文件反而导致拒绝。"""
    if x_connectable():
        return
    # 尝试去掉 XAUTHORITY 再连
    saved = os.environ.pop("XAUTHORITY", None)
    if x_connectable():
        print("[env] X 连接需无认证访问，已自动忽略 XAUTHORITY", file=sys.stderr)
        return
    if saved is not None:
        os.environ["XAUTHORITY"] = saved
    # 最后尝试裸 DISPLAY（无 XDG_RUNTIME_DIR 干扰）
    print(f"[env] 警告: X 显示 {os.environ.get('DISPLAY')} 连接失败，AT-SPI 可能不可用", file=sys.stderr)

load_env()
_ensure_x_connection()
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

def window_visible(window):
    """判断窗口是否在当前显示上：坐标合理（非极端负值）且尺寸正常。

    不依赖屏幕尺寸查询（AT-SPI desktop 组件接口可能阻塞）：
    - 隐藏/最小化窗口通常 extents 为 (x=-1000,y=-1000,w=5,h=5) 或 (x=-99,y=-99,w=1,h=1)
    - 正常窗口 x/y >= 0（或小负数，如标题栏外扩），尺寸 >= 10
    """
    try:
        comp = window.get_component_iface()
        ext = comp.get_extents(Atspi.CoordType.SCREEN)
    except Exception:
        return False
    if ext.width < 10 or ext.height < 10:
        return False
    # 极端负坐标 = 不在当前显示
    if ext.x <= -50 or ext.y <= -50:
        return False
    return True

def find_window(app, index=None, only_visible=True):
    """找应用的窗口(frame)节点，index=None返回第一个，>=0指定第N个（0-based）。
    only_visible=True 时只返回当前屏幕可见的窗口。"""
    targets = []
    def collect(node):
        try: cnt = node.get_child_count()
        except: return
        for j in range(cnt):
            try:
                c = node.get_child_at_index(j)
                if c.get_role_name() == 'frame':
                    if not only_visible or window_visible(c):
                        targets.append(c)
                collect(c)
            except: pass
    collect(app)
    if not targets:
        # 兜底：找任何窗口节点（不过滤可见性）
        for n, _ in find_all_windows(app):
            if not only_visible or window_visible(n):
                targets.append(n)
    if index is None:
        return targets[0] if targets else None
    return targets[index] if 0 <= index < len(targets) else None

def find_all_windows(app):
    """返回 [(node, name), ...] 列表。"""
    results = []
    def rec(node):
        try: cnt = node.get_child_count()
        except: return
        for j in range(cnt):
            try:
                c = node.get_child_at_index(j)
                if c.get_role_name() == 'window':
                    results.append((c, c.get_name() or ''))
                rec(c)
            except: pass
    rec(app)
    return results

def close_window_via_menu(app):
    """通过菜单栏'文件'→'关闭窗口'关闭。返回 True 成功。"""
    import time
    # 找 file menu
    file_menu = find_menu_by_label(app, '文件')
    if not file_menu:
        file_menu = find_menu_by_label(app, 'File')
    if not file_menu:
        return False
    try:
        file_menu.get_action().do_action(0)  # 展开
    except Exception:
        pass
    time.sleep(0.3)
    # 找关闭窗口 / 退出
    for label in ('关闭窗口', '关闭', '退出', 'Quit', 'Exit', '关闭窗口(W)', '退出(Q)'):
        items = find(file_menu, label, 'menu item')
        if items:
            try:
                items[0].get_action().do_action(0)
            except Exception:
                pass
            print(f"已点击: {label}")
            return True
    return False

def close_window_via_button(app):
    """直接找关闭按钮(push button + 含'关闭')。返回 True 成功。"""
    hits = find(app, '关闭', 'push button')
    if not hits:
        hits = find(app, '×', 'push button')
    if hits:
        hits[0].get_action().do_action(0)
        print(f"已点击关闭按钮: {hits[0].get_name()[:60]}")
        return True
    return False

def close_window_keyboard(app):
    """兜底：用 Alt+F4 关闭当前活动窗口（通过 AT-SPI 键盘事件）。"""
    # 激活第一个窗口
    w = find_window(app, 0)
    if w:
        try:
            comp = w.get_component_iface()
            if comp: comp.grab_focus()
        except Exception: pass
    # 发送 Alt+F4
    Atspi.generate_keyboard_event(0xffe9, None, Atspi.KeySynthType.PRESS)   # Alt
    Atspi.generate_keyboard_event(0x77, None, Atspi.KeySynthType.PRESS)     # w
    Atspi.generate_keyboard_event(0x77, None, Atspi.KeySynthType.RELEASE)
    Atspi.generate_keyboard_event(0xffe9, None, Atspi.KeySynthType.RELEASE)
    print("已发送 Alt+F4")

def _xdotool_windows(name):
    """用 xdotool 按窗口标题查窗口 ID 列表（大小写敏感子串匹配）。失败返回 []。"""
    try:
        out = subprocess.run(["xdotool", "search", "--name", name],
                             capture_output=True, text=True, timeout=5).stdout
        return [l.strip() for l in out.splitlines() if l.strip()]
    except Exception:
        return []

def _wait_closed(app_name, timeout=5):
    """轮询 xdotool 确认窗口已消失（关闭成功）。xdotool 不可用时视为成功。"""
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _xdotool_windows(app_name):
            return True
        time.sleep(0.5)
    return False

def close_window_via_xdotool(app):
    """兜底：xdotool windowclose 发送 WM_DELETE 关闭请求。返回 True 已发送。"""
    name = app.get_name()
    if not name:
        return False
    wins = _xdotool_windows(name)
    if not wins:
        return False
    for w in wins:
        subprocess.run(["xdotool", "windowclose", w], capture_output=True, timeout=5)
    print(f"已通过 xdotool 发送关闭请求({len(wins)}个窗口)")
    return True

def find_menu_by_label(node, label):
    """在节点树下找含 label 字符串的 menu 节点。"""
    def rec(n):
        try: cnt = n.get_child_count()
        except: return None
        for j in range(cnt):
            try:
                c = n.get_child_at_index(j)
                if c.get_role_name() == 'menu' and label in (c.get_name() or ''):
                    return c
                r = rec(c)
                if r: return r
            except: pass
        return None
    return rec(node)

def main():
    if len(sys.argv) < 2:
        print("用法: atspi.py apps | tree <app> | click <app> <label> [role] [idx] | close <app> [win_idx] | type <app> <label> <text> | listall")
        print("  close <app> : 通过文件菜单→关闭窗口 优雅关闭应用主窗口")
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
    elif cmd == "close":
        app = find_app(sys.argv[2])
        if not app: print("未找到应用"); return
        force = "--all" in sys.argv
        win_idx = None
        for a in sys.argv[3:]:
            if a.isdigit():
                win_idx = int(a); break
        w = find_window(app, win_idx, only_visible=not force)
        if not w:
            # 未找到可见窗口：列出全部窗口供用户确认
            allw = find_all_windows(app)
            if not allw:
                print("未找到任何窗口"); return
            print(f"未找到当前显示上的窗口（共{len(allw)}个，可能在其他工作区/已最小化）:")
            for i, (n, nm) in enumerate(allw):
                try:
                    ext = n.get_component_iface().get_extents(Atspi.CoordType.SCREEN)
                    pos = f"({ext.x},{ext.y} {ext.width}x{ext.height})"
                except Exception:
                    pos = "(?)"
                print(f"  [{i}] {nm!r} {pos}")
            print("如需强制关闭请用: close <app> --all")
            return
        # 链式关闭：菜单 → 按钮 → Alt+F4 → xdotool，每步后验证窗口是否真消失
        app_name = app.get_name()
        for step, fn in (("菜单", close_window_via_menu),
                         ("按钮", close_window_via_button),
                         ("Alt+F4", close_window_keyboard),
                         ("xdotool", close_window_via_xdotool)):
            if fn(app) and _wait_closed(app_name):
                print(f"已关闭: {app_name}（方式: {step}）")
                break
        else:
            print(f"警告: 所有关闭方式均未生效，{app_name} 窗口可能仍存在")
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
