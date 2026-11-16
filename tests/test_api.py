"""
SupportIQ — API Integration Tests (requires the backend to be running)
Run with: venv\Scripts\python.exe -m pytest tests\test_api.py -v

These tests call the live FastAPI backend.
Start it first with:  venv\Scripts\uvicorn.exe backend.main:app --reload
"""

import sys
import pytest
import requests

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "http://127.0.0.1:8000"


# ==========================================
# SKIP ALL TESTS IF BACKEND IS NOT RUNNING
# ==========================================

def backend_available():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not backend_available(),
    reason="FastAPI backend is not running on http://127.0.0.1:8000"
)


# ==========================================
# HOME + HEALTH TESTS
# ==========================================

class TestHealthEndpoints:

    def test_home(self):
        r = requests.get(f"{BASE_URL}/")
        assert r.status_code == 200
        data = r.json()
        assert "message" in data
        assert "status" in data

    def test_health(self):
        r = requests.get(f"{BASE_URL}/health")
        assert r.status_code == 200
        assert r.json().get("status") == "healthy"


# ==========================================
# TICKET CRUD TESTS
# ==========================================

TICKET_PAYLOAD = {
    "customer_name": "Test User",
    "email": "testuser@example.com",
    "complaint": "My payment failed and I need help urgently."
}

created_ticket_id = None


class TestTicketCRUD:

    def test_create_ticket(self):
        global created_ticket_id
        r = requests.post(f"{BASE_URL}/tickets", json=TICKET_PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "ticket" in data
        assert data["ticket"]["customer_name"] == "Test User"
        assert data["ticket"]["priority"] == "High"
        assert data["ticket"]["status"] == "Open"
        created_ticket_id = data["ticket"]["ticket_id"]

    def test_get_all_tickets(self):
        r = requests.get(f"{BASE_URL}/tickets")
        assert r.status_code == 200
        data = r.json()
        assert "tickets" in data
        assert isinstance(data["tickets"], list)
        assert data["total_tickets"] >= 1

    def test_get_ticket_by_id(self):
        assert created_ticket_id is not None, "Depends on test_create_ticket"
        r = requests.get(f"{BASE_URL}/tickets/{created_ticket_id}")
        assert r.status_code == 200
        ticket = r.json()
        assert ticket["ticket_id"] == created_ticket_id

    def test_get_ticket_not_found(self):
        r = requests.get(f"{BASE_URL}/tickets/nonexistent-id-xyz")
        assert r.status_code == 404

    def test_update_ticket_status(self):
        assert created_ticket_id is not None
        r = requests.patch(
            f"{BASE_URL}/tickets/{created_ticket_id}/status",
            json={"status": "In Progress"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ticket"]["status"] == "In Progress"

    def test_update_invalid_status(self):
        assert created_ticket_id is not None
        r = requests.patch(
            f"{BASE_URL}/tickets/{created_ticket_id}/status",
            json={"status": "Closed"}
        )
        assert r.status_code == 400

    def test_delete_ticket(self):
        assert created_ticket_id is not None
        r = requests.delete(f"{BASE_URL}/tickets/{created_ticket_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["ticket_id"] == created_ticket_id

        # Verify it's gone
        r2 = requests.get(f"{BASE_URL}/tickets/{created_ticket_id}")
        assert r2.status_code == 404

    def test_delete_nonexistent_ticket(self):
        r = requests.delete(f"{BASE_URL}/tickets/ghost-id-xyz")
        assert r.status_code == 404
