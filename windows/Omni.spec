# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
project_root = Path(__file__).resolve().parent.parent if '__file__' in globals() else Path.cwd()
if (project_root / 'windows').name != 'windows' and (Path.cwd() / 'windows').exists():
    project_root = Path.cwd()

datas = [
    (str(project_root / 'resources' / 'AppIcon.ico'), 'resources'),
    (str(project_root / 'omni' / 'ui_config.json'), 'omni'),
    (str(project_root / 'omni' / 'ui' / 'style.css'), 'omni/ui'),
]

hiddenimports = [
    'webview',
    'webview.platforms.winforms',
    'webview.platforms.edgechromium',
    'pystray',
    'pystray._win32',
    'PIL',
    'PIL.Image',
    'PIL.ImageGrab',
    'mss',
    'sounddevice',
    'numpy',
    'edge_tts',
    'google.genai',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
]

a = Analysis(
    ['main_windows.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PyQt6', 'PySide6'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Omni',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'resources' / 'AppIcon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Omni',
)
