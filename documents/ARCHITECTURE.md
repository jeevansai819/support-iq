# SupportIQ — System Architecture

## Overview

SupportIQ follows a three-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                         │
│                 http://localhost:8501                        │
└─────────────────────┬───────────────────────────────────────┘
                      │  HTTP (Streamlit renders in browser)
┌─────────────────────▼───────────────────────────────────────┐
│                   STREAMLIT FRONTEND                        │
│                  frontend/app.py                            │
│                                                             │
│  Pages:                                                     │
│  • Dashboard     — KPIs, charts, recent tickets             │
│  • Create Ticket — Manual ticket entry                      │
│  • All Tickets   — Search, filter, update, delete           │
│  • AI Analysis   — Send complaint to AI + create ticket     │
│  • Export Data   — CSV download with filters                │
└───────────┬─────────────────────────────────────────────────┘
            │  Direct SQLite reads (dashboard, all tickets)
            │  HTTP REST (AI analysis, status updates)
┌───────────▼─────────────────────────────────────────────────┐
│                   FASTAPI BACKEND                           │
│               backend/main.py  :8000                        │
│                                                             │
│  Routes:                                                    │
│  GET  /             — Welcome                               │
│  GET  /health       — Health check                          │
│  POST /ask          — Customer query                        │
│  POST /tickets      — Create ticket (keyword priority)      │
│  GET  /tickets      — List all tickets                      │
│  GET  /tickets/{id} — Get one ticket                        │
│  PATCH /tickets/{id}/status — Update status                 │
│  DELETE /tickets/{id}       — Delete ticket                 │
│  POST /ai/analyze   — AI analysis + ticket creation         │
└───────────┬─────────────────────┬───────────────────────────┘
            │                     │
            │  SQLite             │  HTTP (JSON)
┌───────────▼──────────┐  ┌──────▼──────────────────────────┐
│   SQLite Database    │  │        OLLAMA (local)            │
│   supportiq.db       │  │   http://localhost:11434         │
│                      │  │                                  │
│  Table: tickets      │  │  Model: llama3.2:3b              │
│  • ticket_id         │  │                                  │
│  • customer_name     │  │  Input:  complaint + prompt      │
│  • email             │  │  Output: JSON with:              │
│  • complaint         │  │    category, sentiment,          │
│  • priority          │  │    priority, suggested_response  │
│  • status            │  │                                  │
│  • created_at        │  └─────────────────────────────────┘
│  • category          │
│  • sentiment         │
│  • suggested_response│
│  • ai_analyzed       │
└──────────────────────┘
```

---

## Data Flow: Creating a Manual Ticket

```
User fills form (frontend)
      │
      ▼
classify_priority() [keyword match]
      │
      ▼
database.save_ticket() [SQLite INSERT]
      │
      ▼
Ticket displayed in UI
```

## Data Flow: AI Analysis

```
User fills form (frontend)
      │
      ▼
POST /ai/analyze → FastAPI backend
      │
      ▼
Structured prompt built
      │
      ▼
POST to Ollama (llama3.2:3b) [local HTTP]
      │
      ▼
JSON response parsed + validated
      │
      ▼
database.save_ticket() [ai_analyzed = 1]
      │
      ▼
Result returned to frontend → displayed
```

---

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `backend/main.py` | All FastAPI routes, request validation, error handling |
| `backend/database.py` | SQLite CRUD — used by backend routes |
| `database.py` (root) | SQLite CRUD — used directly by Streamlit frontend |
| `frontend/app.py` | All UI pages, navigation, forms, charts |
| `main.py` (root) | Uvicorn entry point for the backend |
| `run.bat` | Windows launcher: starts backend + frontend |

> **Why two database.py files?**
> The frontend (`frontend/app.py`) runs as a separate process from the backend.
> It imports `database.py` from the project root to read/write the same SQLite file
> without going through the HTTP API (faster for dashboard reads and status updates).
> The backend uses `backend/database.py` which resolves the same `supportiq.db` path.

---

## Priority Classification Logic

```
complaint text (lowercase)
      │
      ▼
Contains any HIGH keyword?  ──Yes──► "High"
(fraud, hacked, urgent,
 payment failed, etc.)
      │No
      ▼
Contains any MEDIUM keyword? ─Yes──► "Medium"
(refund, delivery delay,
 cancel order, etc.)
      │No
      ▼
                             "Low"
```

When AI Analysis is used, the AI model's priority classification overrides
the keyword-based one.

---

## Security Notes

- Ollama runs **entirely locally** — no complaint data leaves the machine.
- The SQLite file is stored in the project root. Restrict filesystem access in production.
- No authentication is implemented. Add OAuth2/JWT before deploying publicly.
- The FastAPI CORS policy is not set — configure `CORSMiddleware` for browser-based access from other origins.
