"""
SupportIQ — AI-Powered Customer Support Platform
Entry point: starts FastAPI backend via uvicorn.

Usage:
    python main.py
    # or use run.bat for a full launch (backend + frontend)
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
