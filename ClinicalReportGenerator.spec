# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata

# 1. Collect Streamlit and its metadata
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all('streamlit')
extra_metadata = copy_metadata('streamlit')

# 2. Collect Cryptography (used by core.license_guard)
crypto_datas, crypto_binaries, crypto_hiddenimports = collect_all('cryptography')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=streamlit_binaries + crypto_binaries,
    datas=[
        ('core', 'core'),
        ('app.py', '.'),
        ('public_key.pem', '.')
    ] + streamlit_datas + crypto_datas + extra_metadata,
    hiddenimports=[
        'docx',
        'reportlab.platypus',
        'reportlab.lib.styles',
        'PIL',
        'pypdf',
        'cryptography',
        'cryptography.hazmat.primitives.serialization',
        'cryptography.hazmat.primitives.asymmetric.padding',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends.default_backend',
    ] + streamlit_hiddenimports + crypto_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ClinicalReportGenerator',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ClinicalReportGenerator',
)
app = BUNDLE(
    coll,
    name='ClinicalReportGenerator.app',
    icon=None,
    bundle_identifier=None,
)
