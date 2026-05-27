import socket
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import getpass
import time
import ctypes
import sys

version = 1.0 #22/2/2026

try:
    from bidi.algorithm import get_display
    BIDI_AVAILABLE = True
except ImportError:
    BIDI_AVAILABLE = False

if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myapp.chat.client")

HOST = "IP"
PORT = 8080

username = getpass.getuser()

#Arabic helpers

def is_arabic(text):
    for ch in text:
        if '\u0600' <= ch <= '\u06FF':
            return True
    return False

def fix_arabic(text):
    if is_arabic(text):
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except ImportError:
            pass
    return text

def on_close_attempt():
    popup = tk.Toplevel(root)
    popup.configure(bg="#0d0d0d")
    popup.resizable(False, False)
    popup.overrideredirect(True)
    popup.grab_set()

    root.update_idletasks()
    rx = root.winfo_x() + root.winfo_width()  // 2
    ry = root.winfo_y() + root.winfo_height() // 2
    pw, ph = 320, 150
    popup.geometry(f"{pw}x{ph}+{rx - pw // 2}+{ry - ph // 2}")

    border = tk.Frame(popup, bg="#00ff88", padx=1, pady=1)
    border.pack(fill="both", expand=True)

    inner2 = tk.Frame(border, bg="#0d0d0d")
    inner2.pack(fill="both", expand=True)

    title_bar2 = tk.Frame(inner2, bg="#111", height=28)
    title_bar2.pack(fill="x")
    title_bar2.pack_propagate(False)
    tk.Label(title_bar2, text="Hold on!", fg="#00ff88", bg="#111",
             font=("Consolas", 9, "bold"), padx=10).pack(side="left", pady=6)

    tk.Label(inner2, text="متهكر انت كده كده ,تقفل متحاولش\nمتهكر برضو انت قفلتو او قفل البرنامج لو حتى\nكده كلمتين اقولك بس عايز",
             fg="#cccccc", bg="#0d0d0d",
             font=("Consolas", 10), justify="center").pack(expand=True, pady=(12, 8))

    def close_popup():
        popup.grab_release()
        popup.destroy()

    ok_btn = tk.Button(inner2, text="OK", command=close_popup,
                       bg="#1a2e22", fg="#00ff88",
                       activebackground="#1e3a2c", activeforeground="#00ff88",
                       relief="flat", bd=0, font=("Consolas", 9, "bold"),
                       cursor="hand2", width=10)
    ok_btn.pack(pady=(0, 14))
    popup.bind("<Return>", lambda e: close_popup())
    popup.bind("<Escape>", lambda e: close_popup())
    ok_btn.focus_set()

_drag_x = 0
_drag_y = 0

def start_drag(event):
    global _drag_x, _drag_y
    _drag_x = event.x
    _drag_y = event.y

def do_drag(event):
    x = root.winfo_x() + event.x - _drag_x
    y = root.winfo_y() + event.y - _drag_y
    root.geometry(f"+{x}+{y}")

def gui_log(msg, tag=""):
    def _do():
        chat_box.config(state=tk.NORMAL)
        ts = time.strftime("%H:%M")
        full = f"{ts}  {fix_arabic(msg)}\n"
        if is_arabic(msg):
            chat_box.insert(tk.END, full, (tag, "rtl"))
        else:
            chat_box.insert(tk.END, full, (tag, "ltr"))
        chat_box.see(tk.END)
        chat_box.config(state=tk.DISABLED)
    root.after(0, _do)

def set_status(text, color="#555"):
    root.after(0, lambda: (status_var.set(text), status_lbl.config(fg=color)))

def enable_input():
    entry.config(state=tk.NORMAL)
    send_btn.config(state=tk.NORMAL)
    entry.focus()

def disable_input():
    entry.config(state=tk.DISABLED)
    send_btn.config(state=tk.DISABLED)

def on_key_release(event):
    text = entry.get()
    if is_arabic(text):
        entry.config(justify="right")
    else:
        entry.config(justify="left")

client = None

def receive_messages():
    while True:
        try:
            data = client.recv(1024)
            if not data:
                break
            gui_log(f"[Hacker]: {data.decode()}", "incoming")
        except OSError:
            break

    gui_log("[!] Disconnected from server.", "error")
    set_status("Disconnected — retrying…", "#ff4444")
    root.after(0, disable_input)
    threading.Thread(target=reconnect_loop, daemon=True).start()


def reconnect_loop():
    global client
    attempt = 1
    while True:
        set_status(f"Reconnecting… (attempt {attempt})", "#ffaa00")
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((HOST, PORT))
            client.send(username.encode())
            gui_log(f"[*] Reconnected to server as {username}", "system")
            set_status(f"Connected  ·  {HOST}:{PORT}", "#00ff88")
            root.after(0, enable_input)
            threading.Thread(target=receive_messages, daemon=True).start()
            return
        except (ConnectionRefusedError, OSError):
            try:
                client.close()
            except OSError:
                pass
            attempt += 1
            time.sleep(3)


def connect():
    global client
    set_status("Connecting…", "#555")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, PORT))
        client.send(username.encode())
        gui_log(f"[*] Connected to server as {username}", "system")
        set_status(f"Connected  ·  {HOST}:{PORT}", "#00ff88")
        root.after(0, enable_input)
        threading.Thread(target=receive_messages, daemon=True).start()
    except (ConnectionRefusedError, OSError):
        try:
            client.close()
        except OSError:
            pass
        gui_log("[!] Could not reach server. Retrying…", "error")
        threading.Thread(target=reconnect_loop, daemon=True).start()


def send_message(event=None):
    msg = entry.get().strip()
    if not msg:
        return
    try:
        client.send(msg.encode())
        gui_log(f"[You]: {msg}", "outgoing")
        entry.delete(0, tk.END)
        entry.config(justify="left")
    except OSError:
        gui_log("[!] Send failed — not connected.", "error")

#GUI

root = tk.Tk()
root.overrideredirect(True)
root.geometry("540x460+400+200")
root.configure(bg="#0d0d0d")

MONO = ("Consolas", 10)
BOLD = ("Consolas", 9, "bold")

#Outer border
border = tk.Frame(root, bg="#00ff88", padx=1, pady=1)
border.pack(fill="both", expand=True)

inner = tk.Frame(border, bg="#0d0d0d")
inner.pack(fill="both", expand=True)

#Title bar
title_bar = tk.Frame(inner, bg="#111", height=32)
title_bar.pack(fill="x")
title_bar.pack_propagate(False)

tk.Label(title_bar, text=f"Chat  ·  |Hacker|", fg="#00ff88", bg="#111",
         font=("Consolas", 10, "bold"), padx=10).pack(side="left", pady=6)

close_btn = tk.Button(title_bar, text="✕", command=on_close_attempt,
                      bg="#111", fg="#555",
                      activebackground="#3a1a1a", activeforeground="#ff4444",
                      relief="flat", bd=0, font=("Consolas", 11, "bold"),
                      cursor="hand2", padx=10)
close_btn.pack(side="right", fill="y")

title_bar.bind("<ButtonPress-1>", start_drag)
title_bar.bind("<B1-Motion>",     do_drag)

#Status bar
status_bar = tk.Frame(inner, bg="#111", height=24)
status_bar.pack(fill="x")
status_bar.pack_propagate(False)
status_var = tk.StringVar(value="Connecting…")
status_lbl = tk.Label(status_bar, textvariable=status_var, fg="#555", bg="#111",
                      font=("Consolas", 8), padx=10)
status_lbl.pack(side="right", pady=4)

#Input bar
bottom = tk.Frame(inner, bg="#111", height=45)
bottom.pack(fill="x", side="bottom")
bottom.pack_propagate(False)

entry = tk.Entry(bottom, bg="#1a1a1a", fg="#e0e0e0", insertbackground="#00ff88",
                 font=("Consolas", 11), relief="flat", bd=0, state=tk.DISABLED,
                 justify="left")
entry.place(x=8, y=8, relwidth=1.0, width=-90, height=29)
entry.bind("<Return>", send_message)
entry.bind("<KeyRelease>", on_key_release)

send_btn = tk.Button(bottom, text="SEND →", bg="#1a2e22", fg="#00ff88",
                     activebackground="#1e3a2c", activeforeground="#00ff88",
                     relief="flat", bd=0, font=BOLD, cursor="hand2",
                     state=tk.DISABLED, command=send_message)
send_btn.place(relx=1.0, x=-82, y=8, width=74, height=29)

#Chat box
chat_box = ScrolledText(inner, bg="#0a0a0a", fg="#ccc", font=MONO,
                        state=tk.DISABLED, relief="flat", bd=0,
                        wrap=tk.WORD, padx=8, pady=6)
chat_box.pack(fill="both", expand=True, padx=6, pady=(4, 4))

#Color tags
chat_box.tag_config("system",   foreground="#444")
chat_box.tag_config("incoming", foreground="#00ccff")
chat_box.tag_config("outgoing", foreground="#00ff88")
chat_box.tag_config("error",    foreground="#ff4444")
chat_box.tag_config("rtl",      justify="right")
chat_box.tag_config("ltr",      justify="left")

root.bind("<Alt-F4>", lambda e: on_close_attempt())

def ensure_bidi_then_connect():
    if not BIDI_AVAILABLE:
        import subprocess
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "python-bidi", "--quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            gui_log("[*] Arabic support installed. Restart for full effect.", "system")
        except Exception:
            gui_log("[*] Tip: run  pip install python-bidi  for proper Arabic.", "system")
    root.after(0, connect)

threading.Thread(target=ensure_bidi_then_connect, daemon=True).start()
root.mainloop()