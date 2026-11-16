
import sqlite3
from pathlib import Path

# ==================================
# DATABASE CONFIGURATION
# ==================================

DB_PATH = Path(__file__).resolve().parent / "supportiq.db"


# ==================================
# DATABASE CONNECTION
# ==================================

def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# ==================================
# CREATE TABLE AND MIGRATE DATABASE
# ==================================

def create_table():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            complaint TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Get existing database columns

    existing_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(tickets)"
        ).fetchall()
    }

    # Add AI-related columns if missing

    new_columns = {
        "category": "TEXT",
        "sentiment": "TEXT",
        "suggested_response": "TEXT",
        "ai_analyzed": "INTEGER NOT NULL DEFAULT 0"
    }

    for column, definition in new_columns.items():

        if column not in existing_columns:

            connection.execute(
                f"ALTER TABLE tickets ADD COLUMN {column} {definition}"
            )

    connection.commit()
    connection.close()


# ==================================
# SAVE TICKET - ALL 11 FIELDS
# ==================================


def save_ticket(ticket):
    connection = get_connection()

    connection.execute("""
        INSERT INTO tickets (
            ticket_id,
            customer_name,
            email,
            complaint,
            priority,
            status,
            created_at,
            category,
            sentiment,
            suggested_response,
            ai_analyzed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket["ticket_id"],
        ticket["customer_name"],
        ticket["email"],
        ticket["complaint"],
        ticket["priority"],
        ticket["status"],
        ticket["created_at"],
        ticket.get("category"),
        ticket.get("sentiment"),
        ticket.get("suggested_response"),
        ticket.get("ai_analyzed", 0)
    ))

    connection.commit()
    connection.close()


# ==================================
# GET ALL TICKETS
# ==================================

def get_all_tickets():

    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM tickets
        ORDER BY created_at DESC
    """).fetchall()

    connection.close()

    return [dict(row) for row in rows]


# ==================================
# GET TICKET BY ID
# ==================================

def get_ticket_by_id(ticket_id):

    connection = get_connection()

    row = connection.execute("""
        SELECT *
        FROM tickets
        WHERE ticket_id = ?
    """, (ticket_id,)).fetchone()

    connection.close()

    if row:
        return dict(row)

    return None


# ==================================
# UPDATE TICKET STATUS
# ==================================

def update_ticket_status(ticket_id, status):

    connection = get_connection()

    cursor = connection.execute("""
        UPDATE tickets
        SET status = ?
        WHERE ticket_id = ?
    """, (status, ticket_id))

    connection.commit()

    updated = cursor.rowcount > 0

    connection.close()

    return updated


# ==================================
# DELETE TICKET
# ==================================

def delete_ticket(ticket_id):

    connection = get_connection()

    cursor = connection.execute("""
        DELETE FROM tickets
        WHERE ticket_id = ?
    """, (ticket_id,))

    connection.commit()

    deleted = cursor.rowcount > 0

    connection.close()

    return deleted


# ==================================
# DATABASE TEST
# ==================================

if __name__ == "__main__":

    create_table()

    tickets = get_all_tickets()

    print("SupportIQ database initialized!")
    print("Database location:", DB_PATH)
    print("Total tickets:", len(tickets))

    if tickets:
        print("Database fields:", list(tickets[0].keys()))
