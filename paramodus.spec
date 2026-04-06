# paramodus.spec
# =============================================================================
# PyInstaller build spec for Paramodus.
#
# Includes:
#   - All Python source code and packages
#   - ui/ folder (HTML, CSS, JS, assets)
#   - llama-server binary (if present in ./bin/)
#
# Usage
# -----
# 1. Build the llama-server binary first (one-time):
#
#      # Standard llama.cpp (works with bartowski Q4_K_M):
#      python scripts/get_llama_server.py --local
#
#      # PrismML fork (for native Q1_0_g128 1-bit kernel):
#      python scripts/get_llama_server.py --local --prismml
#
# 2. Build the exe:
#      pyinstaller paramodus.spec
#
# 3. Distribute the dist/Paramodus/ folder.  The model (~1-4.6 GB) downloads
#    to %USERPROFILE%\.myapp\models\ on first use — NOT bundled in the exe.
#
# =============================================================================

import glob
import os
import sys

block_cipher = None

# ---------------------------------------------------------------------------
# Binary: llama-server + companion DLLs
# ---------------------------------------------------------------------------
# get_llama_server.py --local extracts llama-server.exe AND all DLLs it
# depends on (llama.dll, ggml.dll, etc.) into ./bin/.
# We bundle every file in bin/ so none of the DLLs are missing at runtime.

exe_name = 'llama-server.exe' if sys.platform == 'win32' else 'llama-server'
bin_dir  = 'bin'

extra_binaries = []
if os.path.isdir(bin_dir):
    bin_files = [f for f in glob.glob(os.path.join(bin_dir, '*')) if os.path.isfile(f)]
    # Destination '.' = root of the _internal bundle folder
    extra_binaries = [(f, '.') for f in bin_files]
    for f in bin_files:
        print(f'[paramodus.spec] Bundling {f}')
if not extra_binaries:
    print(
        '[paramodus.spec] WARNING: bin/ is empty or missing.\n'
        '  Run: python scripts/get_llama_server.py --local\n'
        '  The app will fall back to system PATH at runtime.'
    )

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=extra_binaries,
    datas=[
        # UI assets
        ('ui',          'ui'),
        # Local model package
        ('local_model', 'local_model'),
        # Agent code
        ('agents',      'agents'),
        # API bridge
        ('api',         'api'),
    ],
    hiddenimports=[
        # agno submodules loaded at runtime
        'agno.models.openai',
        'agno.models.anthropic',
        'agno.models.google',
        'agno.models.groq',
        'agno.models.openrouter',
        'agno.models.perplexity',
        'agno.models.xai',
        'agno.knowledge.reader.pdf_reader',
        'agno.knowledge.reader.csv_reader',
        'agno.knowledge.reader.text_reader',
        'agno.knowledge.chunking.recursive',
        'agno.vectordb.lancedb',
        'agno.knowledge.embedder.fastembed',
        # fastembed pulls in onnxruntime which has native libs
        'onnxruntime',
        # lancedb / lance
        'lance',
        'lancedb',
        'tantivy',
        # Standard libs used at runtime
        'sqlite3',
        'email',
        'html',
        'http',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude very large unused packages to keep bundle size down
        'tkinter',
        'matplotlib',
        'scipy',
        'notebook',
        'jupyter',
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
    [],
    exclude_binaries=True,
    name='Paramodus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='ui/icon.ico',   # Uncomment and add icon.ico when ready
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # Don't UPX-compress these — they have their own compression or
        # are sensitive to binary modification
        'llama-server.exe',
        '*.onnx',
    ],
    name='Paramodus',
)
