# SupportIQ — AI-Powered Customer Support Platform

SupportIQ is a full-stack customer support ticketing system that uses **Llama 3.2** (running locally via Ollama) to automatically classify complaints, detect customer sentiment, assign priority and generate suggested agent responses.

---

## Features

| Feature | Description |
|---|---|
| 🎫 Ticket Management | Create, view, filter and update support tickets |
| 🤖 AI Complaint Analysis | Llama 3.2 classifies category, sentiment and priority |
| 💬 Suggested Responses | AI generates a professional response for each complaint |
| 🚦 Auto Priority | Keywords automatically set High / Medium / Low priority |
| 📊 Dashboard | Live KPIs, status and priority distribution charts |
| 🔍 Search & Filter | Search by name, email, ticket ID or complaint text |
| 🗑️ Delete Tickets | Remove individual tickets from the All Tickets page |
| 📤 Export CSV | Download filtered tickets as a CSV file |
| 🟢 Backend Status | Sidebar shows live FastAPI connection status |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | **FastAPI** + Uvicorn |
| Frontend UI | **Streamlit** |
| Database | **SQLite** (via Python `sqlite3`) |
| AI Model | **Llama 3.2:3b** via **Ollama** (local) |
| Data Processing | **Pandas** |
| Visualisation | **Altair** (via Streamlit) |

---

## Project Structure

```
supportiq/
├── backend/
│   ├── main.py                  ← FastAPI app (all API routes)
│   └── database.py              ← SQLite operations for backend
├── frontend/
│   └── app.py                   ← Streamlit UI (all pages)
├── tests/
│   ├── test_priority.py         ← Priority classifier unit tests
│   ├── test_database.py         ← Database operation unit tests
│   └── test_api.py              ← API integration tests
├── documents/
│   └── ARCHITECTURE.md          ← System architecture overview
├── database.py                  ← Root DB module (used by frontend)
├── main.py                      ← Entry point (starts uvicorn)
├── requirements.txt             ← Python dependencies
├── run.bat                      ← One-click launcher (Windows)
└── supportiq.db                 ← SQLite database file
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- Llama 3.2 model pulled:
  ```
  ollama pull llama3.2:3b
  ```

### 1. Set up the virtual environment

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

### 2. Launch the application

**Windows (easiest):**
```
run.bat
```

**Manual (two separate terminals):**

Terminal 1 — Backend:
```bash
venv\Scripts\uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 — Frontend:
```bash
venv\Scripts\streamlit run frontend\app.py
```

### 3. Open in your browser

| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| FastAPI backend | http://127.0.0.1:8000 |
| Interactive API docs | http://127.0.0.1:8000/docs |

---

## Running the Tests

```bash
# Unit tests (no backend required)
venv\Scripts\python.exe -m pytest tests\test_priority.py tests\test_database.py -v

# Integration tests (requires the backend to be running)
venv\Scripts\python.exe -m pytest tests\test_api.py -v

# All tests
venv\Scripts\python.exe -m pytest tests\ -v
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Health check |
| POST | `/ask` | Submit a customer query |
| POST | `/tickets` | Create a ticket (keyword priority) |
| GET | `/tickets` | Get all tickets |
| GET | `/tickets/{id}` | Get a ticket by ID |
| PATCH | `/tickets/{id}/status` | Update ticket status |
| DELETE | `/tickets/{id}` | Delete a ticket |
| POST | `/ai/analyze` | AI analysis + ticket creation |

---

## Priority Classification

Keyword matching is applied to the complaint text (case-insensitive):

| Priority | Keywords |
|---|---|
| 🔴 High | fraud, hacked, account compromised, security breach, unauthorized transaction, payment failed, money deducted, double payment, urgent |
| 🟠 Medium | refund, delivery delay, late delivery, cancel order |
| 🟢 Low | everything else |

> When AI Analysis is used, the AI model's priority overrides the keyword-based one.

---

## AI Analysis

The `/ai/analyze` endpoint sends the complaint to Ollama (Llama 3.2:3b) with a structured prompt and returns:

- **Category**: Payment, Refund, Delivery, Account, Technical Support, Other
- **Sentiment**: Positive, Negative, Neutral
- **Priority**: High, Medium, Low
- **Suggested Response**: a professional, empathetic reply to the customer

The result is validated and saved as a ticket with `ai_analyzed = 1`.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `🔴 Backend: Offline` in sidebar | Start the FastAPI backend: `uvicorn backend.main:app --reload` |
| AI Analysis times out | Ollama may be loading the model. Try again in a few seconds. |
| AI returns invalid response | Restart Ollama and ensure `llama3.2:3b` is pulled |
| Database errors | Delete `supportiq.db` to reset, or check file permissions |
