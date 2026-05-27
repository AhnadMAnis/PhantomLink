# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['C2.py'],  # Your main C2 script
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),  # Include Flask templates
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'jinja2',
        'click',
        'itsdangerous',
        'markupsafe',
        'requests',
        'psutil',
        'logging',
        'sys',
        'dashboard',  # Your dashboard module
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'eventlet',  # Exclude problematic eventlet
        'socketio',
        'flask_socketio',
        'gevent',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='C2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='D:\8211\PhantomLink\icon.ico'  # Optional: add your icon
)