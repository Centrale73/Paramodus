# Paramodus
<img width="500" height="500" alt="paramodus-removebg-preview" src="https://github.com/user-attachments/assets/a3689918-d738-42e3-b2ad-56d0698b6a93" />

**Privacy-first, fully offline Windows AI productivity app** powered by the [Bonsai 1-bit LLM](https://prismml.com) and built with Python + pywebview.

---

## Features

| Feature | Detail |
|---|---|
| **Local AI** | Bonsai 8B / 4B / 1.7B — runs 100% on CPU, no cloud calls |
| **RAG** | Drag-and-drop PDF/CSV ingestion via LanceDB + FastEmbed |
| **CRM** | Event tracking, contact logging, seasonal outreach intelligence |
| **Calendar** | Inline event creation with Google Calendar sync (optional) |
| **Custom Table** | Editable sidebar table → forwarded to agent for analysis |
| **Multi-language** | Full UI + agent locale switch: English / Français / Español |
| **Spaces** | Multiple isolated chat workspaces with custom agent instructions |
| **Memory** | Persistent per-user memory via Agno + SQLite |

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Place the Bonsai model in models/
#    e.g. models/Bonsai-8B.gguf

# 3. Place llama-server binary in bin/

# 4. Run
python app.py
```

> **First launch:** Paramodus starts the llama-server automatically. The window appears within ~1 s; the model loads in the background (2–5 min on first cold start).

---

## Language / Locale

Select your language in **Settings → Language**. The full UI and the AI agent's response language both update immediately. The preference is persisted via the `PARAMODUS_LANGUAGE` environment variable.

---

## Google Workspace (optional)

Place a `credentials.json` (Desktop app OAuth 2.0) in the project root and enable the desired services in **Settings → CRM Integrations**. A browser window will open once for OAuth sign-in; a `token.json` is saved locally. No data leaves your machine.

---

## Architecture

```
app.py                  — pywebview entry point, background init
api/bridge.py           — JS ↔ Python API (pywebview.api)
bonsai_agent.py         — Agno agent + RAG knowledge base
database.py             — Chat history, sessions, spaces (SQLite)
crm/
  db.py                 — CRM/events SQLite layer
  crm_agent.py          — Conversational CRM sub-agent
  google_tools.py       — Gmail / Calendar / Contacts / Drive (read-only)
  scheduler.py          — Follow-up reminder scheduler
ui/
  index.html            — Single-page app shell
  js/app.js             — Core UI logic + i18n
  js/crm_panel.js       — CRM & Calendar panels
  js/table_panel.js     — Custom table panel + agent delegate
```

---

## Building (Windows)

```bash
pyinstaller app.spec          # produces dist/Paramodus.exe
# then compile BonsaiSetup.iss with Inno Setup
```

---

## License

Paramodus integrates the Bonsai model by PrismML.  
Bonsai is a trademark of PrismML. This project is an independent integration and is not affiliated with or endorsed by PrismML.  
Model weights are licensed under the [Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0).

© 2026 Centrale73
