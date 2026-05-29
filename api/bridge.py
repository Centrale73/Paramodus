"""
app.py — BonsaiChat pywebview API bridge.

Exposes all methods the HTML/JS frontend calls via window.pywebview.api.
Adapted from Paramodus' bridge but targeting BonsaiChat's simpler, local-only
backend (llama-server + Agno + LanceDB RAG — no cloud provider switching).
"""

import asyncio
import base64
import json
import os
import requests
import subprocess
import sys
import threading
import uuid
import asyncio
import queue
import time
from typing import Optional


def get_resource_path(relative_path: str) -> str:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # For bridge.py located in api/, we go up one level
        base_path = os.path.dirname(os.path.abspath(__file__ + "/.."))
    return os.path.join(base_path, relative_path)



# ---------------------------------------------------------------------------
# Lazy imports — same pattern as Paramodus so the window opens instantly
# ---------------------------------------------------------------------------

def _db_module():
    from database import save_msg, get_history, clear_session, get_all_sessions
    return save_msg, get_history, clear_session, get_all_sessions


def _agent_module():
    import bonsai_agent
    return bonsai_agent


# ---------------------------------------------------------------------------
# Server path helpers
# ---------------------------------------------------------------------------

# prism-ml ships three Q1_0 (1-bit) variants. 8B is the most capable; 1.7B is
# the "fast mode" that runs 3-4x faster on low-end CPUs. The variant is chosen
# via the BONSAI_MODEL env var ("8b" | "4b" | "1.7b"), which the Settings UI
# sets through set_model_variant() below. Defaults to 8b for back-compat.
# Each size is published in its OWN Hugging Face repo (prism-ml/Bonsai-<N>-gguf),
# and the Q1_0 (1-bit) quant inside is named Bonsai-<N>-Q1_0.gguf. 'file' is the
# local on-disk name we resolve in models/; 'repo'/'hf' build the download URL.
_BONSAI_VARIANTS = {
    "8b":  {"file": "Bonsai-8B.gguf",   "repo": "prism-ml/Bonsai-8B-gguf",   "hf": "Bonsai-8B-Q1_0.gguf",   "label": "Paramodus 8B"},
    "4b":  {"file": "Bonsai-4B.gguf",   "repo": "prism-ml/Bonsai-4B-gguf",   "hf": "Bonsai-4B-Q1_0.gguf",   "label": "Paramodus 4B"},
    "1.7b":{"file": "Bonsai-1.7B.gguf", "repo": "prism-ml/Bonsai-1.7B-gguf", "hf": "Bonsai-1.7B-Q1_0.gguf", "label": "Paramodus 1.7B (fast)"},
}


def _active_variant() -> str:
    v = (os.environ.get("BONSAI_MODEL") or "8b").strip().lower()
    return v if v in _BONSAI_VARIANTS else "8b"


def _model_filename() -> str:
    return _BONSAI_VARIANTS[_active_variant()]["file"]


def _model_download_url() -> str:
    meta = _BONSAI_VARIANTS[_active_variant()]
    return f"https://huggingface.co/{meta['repo']}/resolve/main/{meta['hf']}"


def _get_server_paths():
    """
    Finds the llama-server binary and the GGUF model.
    Checks:
    1. Local folder (for installed production apps)
    2. _MEIPASS (for bundled assets, though we exclude large ones in Option 1)
    3. Dev source folder
    """
    if getattr(sys, 'frozen', False):
        # Running as a compiled .exe
        exe_dir = os.path.dirname(sys.executable)
    else:
        # Running as a script
        exe_dir = os.path.dirname(os.path.abspath(__file__ + "/.."))
    
    # --- BINARIES ---
    # Check next to the EXE first (typical for Option 1 install)
    local_bin = os.path.join(exe_dir, "bin", "llama-server.exe" if os.name == "nt" else "llama-server")
    # Check internal _MEIPASS (pyinstaller bundle)
    internal_bin = get_resource_path(os.path.join("bin", "llama-server.exe" if os.name == "nt" else "llama-server"))
    
    if os.path.exists(local_bin):
        llama_bin = local_bin
    else:
        llama_bin = internal_bin

    # --- MODELS ---
    # Filename depends on the active variant (8b / 4b / 1.7b).
    model_file = _model_filename()
    # Check next to the EXE first
    local_model = os.path.join(exe_dir, "models", model_file)
    # Check internal _MEIPASS
    internal_model = get_resource_path(os.path.join("models", model_file))
    # Also check AppData for previously downloaded models
    appdata_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), "Paramodus", "models")
    appdata_model = os.path.join(appdata_dir, model_file)
    
    if os.path.exists(local_model):
        model_path = local_model
    elif os.path.exists(appdata_model):
        model_path = appdata_model
    else:
        model_path = internal_model
        
    return llama_bin, model_path


# ---------------------------------------------------------------------------
# Adaptive llama-server launch flags
# ---------------------------------------------------------------------------

def _total_ram_gb() -> float:
    """Best-effort total system RAM in GB, stdlib only (no psutil)."""
    try:
        if os.name == "nt":
            import ctypes

            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return stat.ullTotalPhys / (1024 ** 3)
        # POSIX (Linux/macOS)
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            return (os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")) / (1024 ** 3)
    except Exception:
        pass
    return 8.0  # conservative fallback


def _detect_discrete_gpu_layers() -> int:
    """Return a sensible -ngl value based on detected hardware.

    Policy (see PR discussion): default to CPU (0). Only offload when a
    *discrete* GPU with real dedicated VRAM is present. Integrated GPUs
    (Intel HD/UHD/Iris, AMD Radeon Vega iGPU) share system RAM and are
    NOT worth offloading an 8B model to — that was the original -ngl 99
    bug on the Intel HD 530. An explicit BONSAI_NGL env var always wins.
    """
    env = os.environ.get("BONSAI_NGL")
    if env is not None:
        try:
            return int(env)
        except ValueError:
            pass

    # NVIDIA: if nvidia-smi reports VRAM, it's a real discrete GPU.
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4,
        )
        if out.returncode == 0 and out.stdout.strip():
            vram_mb = max(int(x) for x in out.stdout.split() if x.strip().isdigit())
            if vram_mb >= 4000:
                return 99   # offload everything we can
            if vram_mb >= 2000:
                return 20   # partial offload for small dGPUs
    except Exception:
        pass

    # Windows: inspect adapters; only trust NON-integrated names with real RAM.
    if os.name == "nt":
        try:
            out = subprocess.run(
                ["wmic", "path", "win32_VideoController",
                 "get", "Name,AdapterRAM", "/format:csv"],
                capture_output=True, text=True, timeout=5,
            )
            integrated = ("intel", "hd graphics", "uhd graphics", "iris", "vega", "radeon graphics")
            best_vram = 0
            for line in out.stdout.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 3:
                    continue
                ram_s, name = parts[1], parts[2].lower()
                if not ram_s.isdigit():
                    continue
                if any(tag in name for tag in integrated):
                    continue  # iGPU -> never offload
                best_vram = max(best_vram, int(ram_s) // (1024 ** 2))
            if best_vram >= 4000:
                return 99
            if best_vram >= 2000:
                return 20
        except Exception:
            pass

    return 0  # CPU-only: correct for iGPU / no-GPU machines


def _detect_launch_flags() -> dict:
    """Adaptive llama-server flags scaled to the host hardware.

    All values are overridable via env vars (BONSAI_NGL / BONSAI_THREADS /
    BONSAI_CTX / BONSAI_BATCH) so power users can A/B test without code
    changes. Designed to 'just work' across machines: tiny laptops get a
    conservative CPU config; a box with a real discrete GPU auto-offloads.
    """
    logical = os.cpu_count() or 4
    # llama.cpp generally prefers physical cores; HT logical threads contend
    # for the same FP units. Estimate physical as half of logical (>2), capped.
    threads = logical if logical <= 2 else max(2, logical // 2)
    threads = min(threads, 8)

    ram_gb = _total_ram_gb()
    if ram_gb <= 8:
        # low-RAM: weights are only ~1.1 GB (Q1_0), so a 4096-token KV cache
        # (~0.6 GB) fits comfortably alongside the OS. Crucially, we must NOT
        # let llama.cpp auto-fit (-c 0) here: it tries the model's full 64K
        # native context, computes a ~9 GB KV cache, and aborts on an 8 GB box.
        ctx, batch = 4096, 256
    elif ram_gb <= 16:
        ctx, batch = 8192, 512
    else:
        ctx, batch = 16384, 512

    ngl = _detect_discrete_gpu_layers()

    # Env overrides (power-user escape hatch).
    def _env_int(name, default):
        try:
            return int(os.environ[name])
        except (KeyError, ValueError):
            return default

    return {
        "ngl": ngl,
        "threads": _env_int("BONSAI_THREADS", threads),
        "ctx": _env_int("BONSAI_CTX", ctx),
        "batch": _env_int("BONSAI_BATCH", batch),
        "ram_gb": round(ram_gb, 1),
        "logical_cpus": logical,
    }


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

class ApiBridge:
    def __init__(self):
        self._window = None
        self._server_process = None
        self._server_ready = False
        self.current_session_id = str(uuid.uuid4())
        self.current_language = 'en'
        self.current_space_id = None
        self.uploaded_filenames = []

        # Background Event Loop for async Agent runs
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True, name="api-loop")
        self._loop_thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def set_window(self, window):
        self._window = window

    def on_window_closed(self):
        """Called when window closes to stop the background loop."""
        self._loop.call_soon_threadsafe(self._loop.stop)
        self.stop_bonsai()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def new_session(self, space_id=None):
        self.current_session_id = str(uuid.uuid4())
        
        if space_id:
            import database
            database.set_session_space(self.current_session_id, space_id)
            self.current_space_id = space_id
            
        return {"status": "success", "session_id": self.current_session_id}

    def list_sessions(self):
        _, get_history, _, get_all_sessions = _db_module()
        return get_all_sessions()

    def switch_session(self, session_id: str):
        self.current_session_id = session_id
        import database
        self.current_space_id = database.get_session_space(session_id)
        return {"status": "success", "session_id": session_id}

    def get_current_session_id(self):
        return self.current_session_id

    def load_history(self):
        _, get_history, _, _ = _db_module()
        return get_history(self.current_session_id)

    def delete_session(self, session_id: str):
        _, _, clear_session, _ = _db_module()
        clear_session(session_id)
        if self.current_session_id == session_id:
            self.new_session()
        return {"status": "success", "session_id": session_id}

    # ------------------------------------------------------------------
    # Settings & Configuration
    # ------------------------------------------------------------------

    def set_language(self, language: str):
        self.current_language = language
        return {"status": "success"}

    # ------------------------------------------------------------------
    # Spaces management
    # ------------------------------------------------------------------

    def create_space(self, name, description, instructions):
        import database
        space_id = str(uuid.uuid4())
        database.create_space(space_id, name, description, instructions)
        return {"status": "success", "space_id": space_id}

    def list_spaces(self):
        import database
        return database.get_spaces()

    def delete_space(self, space_id):
        import database
        database.delete_space(space_id)
        if self.current_space_id == space_id:
            self.current_space_id = None
        return {"status": "success"}
        
    def get_current_space_id(self):
        return self.current_space_id

    def get_crm_settings(self):
        return {
            "google_calendar_enabled": os.environ.get("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true",
            "google_gmail_enabled": os.environ.get("GOOGLE_GMAIL_ENABLED", "false").lower() == "true",
            "google_contacts_enabled": os.environ.get("GOOGLE_CONTACTS_ENABLED", "false").lower() == "true",
            "google_drive_enabled": os.environ.get("GOOGLE_DRIVE_ENABLED", "false").lower() == "true",
        }

    def set_google_settings(self, settings: dict):
        try:
            import dotenv
            env_file = os.path.join(os.path.dirname(os.path.abspath(__file__ + "/..")), ".env")
            if not os.path.exists(env_file):
                open(env_file, 'a').close()
            
            for key, val in settings.items():
                env_key = key.upper()
                dotenv.set_key(env_file, env_key, "true" if val else "false")
                os.environ[env_key] = "true" if val else "false"
                
                if key == "google_calendar_enabled":
                    import crm.scheduler
                    crm.scheduler.GOOGLE_CALENDAR_ENABLED = val
            
            # If any are true, trigger auth
            if any(settings.values()):
                from crm.google_auth import trigger_auth
                trigger_auth()
                
                if settings.get("google_calendar_enabled"):
                    from crm import start_scheduler
                    start_scheduler()
                    
            return {"status": "success", "settings": settings}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # CRM — exposed to JS via window.pywebview.api
    # ------------------------------------------------------------------

    def get_urgent_events(self):
        """Return all events with urgency tags for the current month."""
        try:
            from crm.db import get_urgent_events
            events = get_urgent_events()
            return {"events": events}
        except Exception as e:
            return {"events": [], "error": str(e)}

    def add_crm_event(self, event_name: str, city: str = "", event_type: str = "",
                      contact_month_start: int = None, contact_month_end: int = None,
                      notes: str = ""):
        """Add a new event/organisation to the CRM."""
        try:
            from crm.db import add_event
            eid = add_event(
                event_name=event_name,
                city=city,
                event_type=event_type,
                contact_month_start=contact_month_start,
                contact_month_end=contact_month_end,
                notes=notes,
            )
            return {"status": "success", "id": eid}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def log_crm_contact(self, org_id: int, status: str, summary: str,
                        follow_up_date: str = "", method: str = "UI"):
        """Log a contact interaction for an organisation."""
        try:
            from crm.db import log_contact
            lid = log_contact(
                org_id=org_id,
                status=status,
                summary=summary,
                follow_up_date=follow_up_date,
                method=method,
            )
            return {"status": "success", "id": lid}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_org_emails(self, org_id: int, limit: int = 5):
        """Suivi des courriels: return recent Gmail messages for an organisation.

        Looks up the organisation's contact_email, then queries Gmail
        (read-only) for the most recent messages from that address. Requires
        the Gmail toggle to be enabled and credentials.json + an authorised
        token to be present. Never raises to JS — returns a status dict.
        """
        try:
            # Respect the Gmail read-only toggle.
            if os.environ.get("GOOGLE_GMAIL_ENABLED", "false").lower() != "true":
                return {
                    "status": "error",
                    "message": "Gmail (lecture seule) n'est pas activé. Activez-le dans Réglages.",
                }

            from crm.db import get_organisation
            org = get_organisation(org_id)
            if not org:
                return {"status": "error", "message": "Organisme introuvable."}

            email = (org.get("contact_email") or "").strip()
            if not email:
                return {
                    "status": "error",
                    "message": "Aucune adresse courriel enregistrée pour cet organisme.",
                }

            from crm.google_tools import _get_service
            service = _get_service("gmail", "v1")
            if not service:
                return {
                    "status": "error",
                    "message": "Gmail indisponible : identifiants manquants ou autorisation requise.",
                    "email": email,
                }

            try:
                lim = max(1, min(int(limit or 5), 20))
            except (TypeError, ValueError):
                lim = 5

            # Pull messages from OR to this address (full thread visibility).
            query = f"from:{email} OR to:{email}"
            listing = service.users().messages().list(
                userId="me", q=query, maxResults=lim
            ).execute()
            messages = listing.get("messages", [])

            emails = []
            for msg in messages:
                data = service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()
                headers = data.get("payload", {}).get("headers", [])
                emails.append({
                    "subject": next((h["value"] for h in headers if h["name"] == "Subject"), "(sans objet)"),
                    "from": next((h["value"] for h in headers if h["name"] == "From"), ""),
                    "date": next((h["value"] for h in headers if h["name"] == "Date"), ""),
                    "snippet": data.get("snippet", ""),
                })

            return {"status": "success", "emails": emails, "email": email}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # Local model / server lifecycle
    # ------------------------------------------------------------------

    def get_local_model_status(self, model_key: str = "bonsai-8b") -> dict:
        return {
            "server_running": self._server_ready,
            "downloaded": self._is_model_present(),
            "model_key": model_key,
        }

    def get_bonsai_models(self) -> list:
        """List all selectable 1-bit variants for the Settings UI."""
        active = _active_variant()
        out = []
        for key, meta in _BONSAI_VARIANTS.items():
            out.append({
                "key": key,
                "name": meta["label"],
                "description": {
                    "8b": "Most capable. ~4-8 tok/s on an older CPU.",
                    "4b": "Balanced. Roughly 2x faster than 8B.",
                    "1.7b": "Fast mode. 3-4x faster; best for low-end hardware.",
                }.get(key, "1-bit quantized LLM — runs entirely on CPU"),
                "active": key == active,
            })
        return out

    def get_model_variant(self) -> str:
        """Return the currently selected variant key (8b/4b/1.7b)."""
        return _active_variant()

    def set_model_variant(self, key: str) -> dict:
        """Switch the active 1-bit variant. Takes effect on next server start;
        the caller should stop_bonsai() then begin_auto_setup() to apply it.
        Persisted via the BONSAI_MODEL env var for this process."""
        key = (key or "").strip().lower()
        if key not in _BONSAI_VARIANTS:
            return {"status": "error",
                    "message": f"Unknown variant '{key}'. Choose 8b, 4b, or 1.7b."}
        os.environ["BONSAI_MODEL"] = key
        return {"status": "ok", "active": key,
                "downloaded": self._is_model_present(),
                "restart_required": True}

    def _is_model_present(self) -> bool:
        _, model_path = _get_server_paths()
        return os.path.isfile(model_path)

    def _download_model(self, url: str, save_path: str, report_cb):
        """Downloads the model while reporting progress to the UI."""
        # Use APPDATA for downloads so they persist even if the app is re-installed or moved
        appdata_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), "Paramodus", "models")
        os.makedirs(appdata_dir, exist_ok=True)
        persistent_path = os.path.join(appdata_dir, os.path.basename(save_path))
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(persistent_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = (downloaded / total_size) * 100
                            # Report progress every ~1% or at the end
                            if int(pct) % 2 == 0 or downloaded == total_size:
                                report_cb("downloading", pct, f"Downloading Model: {pct:.1f}%")

            return True
        except Exception as e:
            report_cb("error", -1, f"Download failed: {e}")
            return False

    # begin_auto_setup — called by JS on pywebviewready
    def begin_auto_setup(self, model_key: str = "bonsai-8b") -> dict:
        def _report(phase: str, pct: float, msg: str):
            if self._window:
                self._window.evaluate_js(
                    f"onBonsaiSetupProgress({json.dumps(phase)}, {pct:.2f}, {json.dumps(msg)})"
                )

        def _worker():
            llama_bin, model_path = _get_server_paths()

            # 1. Binary check
            if not os.path.isfile(llama_bin):
                _report("error", -1,
                        f"llama-server not found at {llama_bin}. "
                        "Place it in the bin/ folder.")
                return

            # 2. Model check
            if not os.path.isfile(model_path):
                _report("downloading", 0, "Model not found. Starting download from Hugging Face...")
                # IMPORTANT: fetch the Q1_0 (1-bit, ~1 GB) quant for the active
                # variant — NOT the repo's default F16 master (~16 GB), which
                # won't fit in RAM. The Q1_0 file is what makes Bonsai 1-bit at
                # runtime. URL tracks the BONSAI_MODEL variant (8b/4b/1.7b).
                model_url = _model_download_url()
                success = self._download_model(model_url, model_path, _report)
                if not success:
                    return # Error already reported by helper

            # 3. Start server with hardware-adaptive flags.
            flags = _detect_launch_flags()
            gpu_desc = (f"GPU offload ({flags['ngl']} layers)"
                        if flags["ngl"] > 0 else "CPU")
            _report("starting", 0,
                    f"Loading model… {gpu_desc}, {flags['threads']} threads, "
                    f"ctx {flags['ctx']} ({flags['ram_gb']} GB RAM)")

            def _build_command(ctx_value):
                """ctx_value: '0' for auto-fit, or a concrete token count string."""
                return [
                    llama_bin,
                    "-m", model_path,
                    "--host", "127.0.0.1",
                    "--port", "8081",
                    "-ngl", str(flags["ngl"]),
                    "-t", str(flags["threads"]),
                    "-c", str(ctx_value),
                    "-b", str(flags["batch"]),
                    # Bonsai (Qwen3-based) recommended sampler, from prism-ml's
                    # canonical start_llama_server.ps1.
                    "--temp", "0.5",
                    "--top-p", "0.85",
                    "--top-k", "20",
                    "--min-p", "0",
                    # Disable hidden "thinking" tokens — Bonsai is a Qwen3 model
                    # and will otherwise burn time reasoning before every reply,
                    # which on CPU feels like the app is frozen. Biggest
                    # perceived-latency win on low-end hardware.
                    "--reasoning-budget", "0",
                    "--reasoning-format", "none",
                    # NOTE: older prism-ml builds took
                    # --chat-template-kwargs '{"enable_thinking": false}',
                    # but build b8846+ deprecated that and ignores it (thinking
                    # stays ON). The current binary wants --reasoning off.
                    "--reasoning", "off",
                ]

            startupinfo = None
            if os.name == "nt":
                import subprocess as _sp
                startupinfo = _sp.STARTUPINFO()
                startupinfo.dwFlags |= _sp.STARTF_USESHOWWINDOW

            # Context strategy. -c 0 (auto-fit) is convenient on big machines
            # but DANGEROUS on low-RAM boxes: it sizes the KV cache for the
            # model's full 64K native context (~9 GB) and aborts before it ever
            # listens. So only attempt auto-fit when there's plenty of RAM;
            # otherwise go straight to the fixed, hardware-scaled context.
            if flags["ram_gb"] > 16:
                ctx_attempts = ["0", str(flags["ctx"])]
            else:
                ctx_attempts = [str(flags["ctx"])]
            for attempt_idx, ctx_value in enumerate(ctx_attempts):
                command = _build_command(ctx_value)
                ctx_label = "auto-fit" if ctx_value == "0" else f"ctx {ctx_value}"
                _report("starting", 0, f"Loading model… {ctx_label}")
                saw_ctx_error = False
                try:
                    self._server_process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        startupinfo=startupinfo,
                        text=True,
                        bufsize=1,
                    )

                    for line in self._server_process.stdout:
                        stripped = line.strip()
                        if stripped:
                            _report("starting", 0, stripped[:90])

                        low = line.lower()
                        # Signs the context flag was rejected by this build.
                        if ("-c 0" in low or "ctx" in low) and (
                            "unknown" in low or "invalid" in low or "unsupported" in low
                        ):
                            saw_ctx_error = True

                        if "HTTP server error" in line:
                            _report("error", -1,
                                    "Server failed to start — port 8081 may be in use.")
                            return

                        if "server is listening on" in line:
                            self._server_ready = True
                            try:
                                _agent_module().init_agent()
                            except Exception as e:
                                _report("error", -1, f"Agent init failed: {e}")
                                return
                            _report("ready", 100, "Bonsai is ready")
                            return

                    # stdout closed without "listening" -> process exited early.
                    can_retry = attempt_idx + 1 < len(ctx_attempts)
                    if can_retry and (saw_ctx_error or ctx_value == "0"):
                        _report("starting", 0,
                                "Auto-fit context not supported — retrying with a "
                                "fixed context size…")
                        continue
                    _report("error", -1,
                            "Server exited before it was ready. Check that "
                            "bin/llama-server.exe is the prism-ml Q1_0 build and "
                            "models/Bonsai-8B.gguf is the Q1_0 quant.")
                    return
                except Exception as e:
                    _report("error", -1, f"Failed to launch server: {e}")
                    return

        threading.Thread(target=_worker, daemon=True, name="bonsai-server").start()
        return {"status": "started"}

    def stop_bonsai(self) -> dict:
        if self._server_process and self._server_process.poll() is None:
            self._server_process.kill()
        self._server_ready = False
        return {"status": "stopped"}

    # Stub out download methods (model is shipped or user places it manually)
    def download_bonsai(self, model_key: str = "bonsai-8b") -> dict:
        return {"status": "not_applicable",
                "message": "Paramodus does not auto-download. Place the .gguf in models/."}

    def cancel_download_bonsai(self, model_key: str = "bonsai-8b") -> dict:
        return {"status": "not_applicable"}

    # ------------------------------------------------------------------
    # RAG / file handling
    # ------------------------------------------------------------------

    def clear_rag_context(self):
        try:
            success = _agent_module().clear_knowledge_base()
        except Exception as e:
            return f"Error clearing RAG: {e}"
        self.uploaded_filenames = []
        return "RAG context cleared" if success else "Error clearing RAG context"

    def upload_files(self, files_json):
        try:
            files_data = json.loads(files_json) if isinstance(files_json, str) else files_json
            processed = []
            for f in files_data:
                name = f["name"]
                content_b64 = f["content"]
                if "," in content_b64:
                    content_b64 = content_b64.split(",")[1]
                data = base64.b64decode(content_b64)
                processed.append({"name": name, "data": data})
                self.uploaded_filenames.append(name)

            success = asyncio.run(_agent_module().aingest_files(processed))
            if success:
                return {"status": "success", "files": list(set(self.uploaded_filenames))}
            return {"status": "error", "message": "Failed to ingest files"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # Chat streaming
    # ------------------------------------------------------------------

    def start_chat_stream(self, user_text: str, target_id: str = None):
        if not self._server_ready:
            if self._window:
                self._window.evaluate_js(
                    "receiveError('Bonsai is still starting up — please wait a moment.')"
                )
            return

        if not target_id:
            save_msg, _, _, _ = _db_module()
            save_msg("user", user_text, self.current_session_id)

        # Schedule the async run in our background loop
        asyncio.run_coroutine_threadsafe(
            self._run_chat_async(user_text, target_id),
            self._loop
        )

    async def _run_chat_async(self, user_text: str, target_id: str):
        try:
            agent = _agent_module().get_agent(self.current_session_id, self.current_language)
            full_response = ""
            
            # Fetch space instructions if any
            import database
            space_instructions = ""
            if self.current_space_id:
                space = database.get_space(self.current_space_id)
                if space and space["instructions"]:
                    space_instructions = space["instructions"]
            
            run_kwargs = _agent_module().get_run_kwargs(self.current_session_id, self.current_language, space_instructions)
            run_response = agent.arun(user_text, stream=True, **run_kwargs)

            if target_id and self._window:
                self._window.evaluate_js(f"clearBubble('{target_id}')")

            # Batch chunks to avoid "Maximum recursion depth" in pywebview
            chunk_buffer = ""
            last_send_time = time.time()

            async for chunk in run_response:
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if content:
                    full_response += content
                    chunk_buffer += content
                    
                    # Send every 50ms or if buffer is large
                    if time.time() - last_send_time > 0.05 or len(chunk_buffer) > 100:
                        if self._window:
                            self._window.evaluate_js(
                                f"receiveChunk({json.dumps(chunk_buffer)}, '{target_id or ''}')"
                            )
                        chunk_buffer = ""
                        last_send_time = time.time()

            # Send remaining buffer
            if chunk_buffer and self._window:
                self._window.evaluate_js(
                    f"receiveChunk({json.dumps(chunk_buffer)}, '{target_id or ''}')"
                )

            save_msg, _, _, _ = _db_module()
            save_msg("bot", full_response, self.current_session_id)

            tone = self._detect_tone(full_response)
            if self._window:
                self._window.evaluate_js(f"streamComplete({json.dumps(tone)})")

        except Exception as e:
            if self._window:
                self._window.evaluate_js(f"receiveError({json.dumps(str(e))})")

    # ------------------------------------------------------------------
    # Tone detection (carried over from Paramodus)
    # ------------------------------------------------------------------

    def _detect_tone(self, text: str) -> str:
        t = text.lower()
        scores = {"excited": 0, "playful": 0, "serious": 0, "calm": 0}

        for w in ["!", "amazing", "awesome", "fantastic", "great", "excellent",
                  "wonderful", "exciting", "incredible", "brilliant", "love"]:
            scores["excited"] += t.count(w)

        for w in ["😊", "😄", "🎉", "haha", "fun", "enjoy", "play", "joke",
                  "funny", "silly", "cool", "👍", "✨"]:
            scores["playful"] += t.count(w)

        for w in ["important", "critical", "warning", "caution", "error",
                  "must", "should", "require", "necessary", "essential",
                  "security", "risk", "issue", "problem", "careful"]:
            scores["serious"] += t.count(w)

        for w in ["here", "let me", "simply", "just", "easy", "step", "guide",
                  "help", "explain", "understand", "note", "consider"]:
            scores["calm"] += t.count(w)

        return max(scores, key=scores.get) if max(scores.values()) > 0 else "calm"
