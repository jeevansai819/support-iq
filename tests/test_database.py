"""
SupportIQ — Database Unit Tests
Run with: venv\Scripts\python.exe -m pytest tests\ -v
"""

import sys
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ==========================================
# FIXTURES — Use an in-memory or temp DB
# ==========================================

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Redirect database.DB_PATH to a temporary file for each test."""
    import database

    db_file = tmp_path / "test_supportiq.db"
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.create_table()
    return database


# ==========================================
# SCHEMA TESTS
# ==========================================

class TestCreateTable:

    def test_table_created(self, temp_db):
        conn = temp_db.get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        conn.close()
        assert "tickets" in table_names

    def test_all_columns_exist(self, temp_db):
        conn = temp_db.get_connection()
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(tickets)").fetchall()
        }
        conn.close()
        expected = {
            "ticket_id", "customer_name", "email", "complaint",
            "priority", "status", "created_at",
            "category", "sentiment", "suggested_response", "ai_analyzed"
        }
        assert expected.issubset(cols)

    def test_idempotent_create(self, temp_db):
        """Calling create_table twice should not raise."""
        temp_db.create_table()
        temp_db.create_table()


# ==========================================
# SAVE + RETRIEVE TESTS
# ==========================================

SAMPLE_TICKET = {
    "ticket_id": "test-001",
    "customer_name": "Alice Smith",
    "email": "alice@example.com",
    "complaint": "My payment failed",
    "priority": "High",
    "status": "Open",
    "created_at": "2026-11-16T10:00:00",
    "category": None,
    "sentiment": None,
    "suggested_response": None,
    "ai_analyzed": 0
}

AI_TICKET = {
    "ticket_id": "test-002",
    "customer_name": "Bob Jones",
    "email": "bob@example.com",
    "complaint": "My refund has not arrived",
    "priority": "Medium",
    "status": "Open",
    "created_at": "2026-11-16T11:00:00",
    "category": "Refund",
    "sentiment": "Negative",
    "suggested_response": "Dear Bob, we are looking into your refund.",
    "ai_analyzed": 1
}


class TestSaveTicket:

    def test_save_basic_ticket(self, temp_db):
        temp_db.save_ticket(SAMPLE_TICKET)
        tickets = temp_db.get_all_tickets()
        assert len(tickets) == 1
        assert tickets[0]["ticket_id"] == "test-001"

    def test_save_ai_ticket(self, temp_db):
        temp_db.save_ticket(AI_TICKET)
        ticket = temp_db.get_ticket_by_id("test-002")
        assert ticket["category"] == "Refund"
        assert ticket["sentiment"] == "Negative"
        assert ticket["ai_analyzed"] == 1

    def test_duplicate_ticket_id_raises(self, temp_db):
        temp_db.save_ticket(SAMPLE_TICKET)
        with pytest.raises(Exception):
            temp_db.save_ticket(SAMPLE_TICKET)


class TestGetAllTickets:

    def test_empty_returns_list(self, temp_db):
        assert temp_db.get_all_tickets() == []

    def test_returns_all(self, temp_db):
        temp_db.save_ticket(SAMPLE_TICKET)
        temp_db.save_ticket(AI_TICKET)
        tickets = temp_db.get_all_tickets()
        assert len(tickets) == 2

    def test_ordered_by_created_at_desc(self, temp_db):
        temp_db.save_ticket(SAMPLE_TICKET)   # earlier
        temp_db.save_ticket(AI_TICKET)       # later
        tickets = temp_db.get_all_tickets()
        assert tickets[0]["ticket_id"] == "test-002"


class TestGetTicketById:

    def test_found(self, temp_db):
        temp_db.save_ticket(SAMPLE_TICKET)
        ticket = temp_db.get_ticket_by_id("test-001")
        assert ticket is not None
        assert ticket["customer_name"] == "Alice Smith"

    def test_not_found_returns_none(self, temp_db):
        result = temp_db.get_ticket_by_id("does-not-exist")
        assert result is None


# ==========================================
# UPDATE STATUS TESTS
# ==========================================

class TestUpdateTicketStatus:

    def test_update_status(self, temp_db):
        temp_db.save_ticket(SAMPLE_TICKET)
        updated = temp_db.update_ticket_status("test-001", "Resolved")
        assert updated is True
        ticket = temp_db.get_ticket_by_id("test-001")
        assert ticket["status"] == "Resolved"

    def test_update_nonexistent_returns_false(self, temp_db):
        result = temp_db.update_ticket_status("ghost-id", "Resolved")
        assert result is False


# ==========================================
# DELETE TICKET TESTS
# ==========================================

class TestDeleteTicket:

    def test_delete_existing(self, temp_db):
        temp_db.save_ticket(SAMPLE_TICKET)
        deleted = temp_db.delete_ticket("test-001")
        assert deleted is True
        assert temp_db.get_ticket_by_id("test-001") is None

    def test_delete_nonexistent_returns_false(self, temp_db):
        result = temp_db.delete_ticket("ghost-id")
        assert result is False

    def test_other_tickets_unaffected(self, temp_db):
        temp_db.save_ticket(SAMPLE_TICKET)
        temp_db.save_ticket(AI_TICKET)
        temp_db.delete_ticket("test-001")
        remaining = temp_db.get_all_tickets()
        assert len(remaining) == 1
        assert remaining[0]["ticket_id"] == "test-002"
