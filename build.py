"""
build.py — One-command Paramodus .exe builder.

Usage:
    python build.py

What it does:
    1. Downloads llama-server.exe into ./bin/ (skipped if already present)
    2. Runs PyInstaller with paramodus.spec
    3. Prints the path to the final .exe

The end user receives dist/Paramodus.exe and never touches a terminal.
"""

import subprocess
import sys
import os
import shutil


def main():
    root = os.path.dirname(os.path.abspath(__file__))

    # ── Step 1: llama-server binary ───────────────────────────────────────────
    exe_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    bin_path  = os.path.join(root, "bin", exe_name)

    if os.path.isfile(bin_path):
        print(f"[build] llama-server already in bin/ — skipping download.")
    else:
        print("[build] Downloading llama-server binary…")
        result = subprocess.run(
            [sys.executable, os.path.join(root, "scripts", "get_llama_server.py"), "--local"],
            check=False,
        )
        if result.returncode != 0:
            print("[build] ERROR: Failed to download llama-server. Check your internet connection.")
            sys.exit(1)
        if not os.path.isfile(bin_path):
            print(f"[build] ERROR: Expected binary not found at {bin_path}")
            sys.exit(1)
        print(f"[build] llama-server ready at {bin_path}")

    # ── Step 2: PyInstaller ───────────────────────────────────────────────────
    if shutil.which("pyinstaller") is None:
        print("[build] PyInstaller not found — installing…")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    spec = os.path.join(root, "paramodus.spec")
    print("[build] Running PyInstaller…")
    result = subprocess.run(
        ["pyinstaller", spec, "--clean", "--noconfirm"],
        check=False,
    )
    if result.returncode != 0:
        print("[build] ERROR: PyInstaller failed.")
        sys.exit(1)

    # ── Done ──────────────────────────────────────────────────────────────────
    exe_name_out = "Paramodus.exe" if sys.platform == "win32" else "Paramodus"
    dist_path    = os.path.join(root, "dist", exe_name_out)
    if os.path.isfile(dist_path):
        size_mb = os.path.getsize(dist_path) / (1024 ** 2)
        print(f"\n[build] ✓ Done — {dist_path} ({size_mb:.0f} MB)")
        print("[build]   Distribute this file. End users just open it.")
    else:
        print(f"\n[build] Build finished. Check the dist/ folder.")


if __name__ == "__main__":
    main()
