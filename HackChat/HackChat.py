import socket
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import time

version = 1.0 #22/2/2026

HOST = "0.0.0.0"
PORT = 8080

connected_client = None
client_username  = None

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

def listen_for_messages():
    global connected_client, client_username
    while True:
        try:
            data = connected_client.recv(1024)
            if not data:
                break
            gui_log(f"[{client_username}]: {data.decode()}", "incoming")
        except OSError:
            break

    gui_log(f"[*] {client_username} disconnected.", "system")
    set_status("Waiting for connection…", "#555")
    connected_client = None
    client_username  = None
    root.after(0, disable_input)
    threading.Thread(target=accept_one_client, daemon=True).start()


def accept_one_client():
    global connected_client, client_username

    gui_log("[*] Waiting for client to connect…", "system")
    set_status("Waiting for connection…", "#555")

    client_sock, addr = server_socket.accept()
    connected_client = client_sock

    try:
        client_username = client_sock.recv(1024).decode().strip() or f"User@{addr[0]}"
    except OSError:
        client_username = f"User@{addr[0]}"

    gui_log(f"[+] {client_username} connected from {addr[0]}:{addr[1]}", "system")
    set_status(f"Chatting with  {client_username}", "#00ff88")
    root.after(0, enable_input)
    threading.Thread(target=listen_for_messages, daemon=True).start()


def send_message(event=None):
    msg = entry.get().strip()
    if not msg or connected_client is None:
        return
    try:
        connected_client.send(msg.encode())
        gui_log(f"[You]: {msg}", "outgoing")
        entry.delete(0, tk.END)
    except OSError:
        gui_log("[!] Send failed — client disconnected.", "error")

def enable_input():
    entry.config(state=tk.NORMAL)
    send_btn.config(state=tk.NORMAL)
    entry.focus()

def disable_input():
    entry.config(state=tk.DISABLED)
    send_btn.config(state=tk.DISABLED)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(1)

root = tk.Tk()
root.title("Chat Server")
root.geometry("540x460")
root.minsize(400, 320)
root.configure(bg="#0d0d0d")

MONO = ("Consolas", 10)
BOLD = ("Consolas", 9, "bold")

top = tk.Frame(root, bg="#111")
top.pack(fill="x")
tk.Label(top, text="SERVER", fg="#00ff88", bg="#111",
         font=("Consolas", 12, "bold"), padx=12, pady=8).pack(side="left")
status_var = tk.StringVar(value="Starting…")
status_lbl = tk.Label(top, textvariable=status_var, fg="#555", bg="#111", font=BOLD, padx=12)
status_lbl.pack(side="right")

chat_box = ScrolledText(root, bg="#0a0a0a", fg="#ccc", font=MONO,
                        state=tk.DISABLED, relief="flat", bd=0,
                        wrap=tk.WORD, padx=8, pady=6)
chat_box.pack(fill="both", expand=True, padx=8, pady=6)
chat_box.tag_config("system",   foreground="#444")
chat_box.tag_config("incoming", foreground="#00ccff")
chat_box.tag_config("outgoing", foreground="#00ff88")
chat_box.tag_config("error",    foreground="#ff4444")

chat_box.tag_config("rtl", justify="right")
chat_box.tag_config("ltr", justify="left")

bottom = tk.Frame(root, bg="#111")
bottom.pack(fill="x", side="bottom")

entry = tk.Entry(bottom, bg="#1a1a1a", fg="#e0e0e0", insertbackground="#00ff88",
                 font=MONO, relief="flat", bd=0, state=tk.DISABLED)
entry.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=8)
entry.bind("<Return>", send_message)

send_btn = tk.Button(bottom, text="SEND →", bg="#1a2e22", fg="#00ff88",
                     activebackground="#1e3a2c", activeforeground="#00ff88",
                     relief="flat", bd=0, font=BOLD, cursor="hand2",
                     state=tk.DISABLED, command=send_message)
send_btn.pack(side="left", padx=(0, 8), pady=8, ipadx=10)

threading.Thread(target=accept_one_client, daemon=True).start()
root.mainloop()