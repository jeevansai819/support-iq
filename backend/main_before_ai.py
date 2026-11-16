
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timezone

from database import (
    create_table,
    save_ticket,
    get_all_tickets as db_get_all_tickets,
    get_ticket_by_id,
    update_ticket_status as db_update_ticket_status
)

app = FastAPI(
    title="SupportIQ",
    description="AI Powered Customer Support Platform",
    version="1.0.0"
)

# Initialize SQLite database
create_table()


# Customer query structure
class CustomerQuery(BaseModel):
    customer_name: str
    question: str


# Ticket creation structure
class TicketRequest(BaseModel):
    customer_name: str
    email: str
    complaint: str


# Ticket status update structure
class TicketStatusUpdate(BaseModel):
    status: str


# Determine ticket priority
def classify_priority(complaint):

    text = complaint.lower()

    high_keywords = [
        "payment failed",
        "fraud",
        "hacked",
        "money deducted",
        "urgent"
    ]

    medium_keywords = [
        "refund",
        "delivery delay",
        "late delivery",
        "cancel order"
    ]

    if any(word in text for word in high_keywords):
        return "High"

    elif any(word in text for word in medium_keywords):
        return "Medium"

    else:
        return "Low"


# Home endpoint
@app.get("/")
def home():

    return {
        "message": "Welcome to SupportIQ!",
        "status": "Application is running"
    }


# Health endpoint
@app.get("/health")
def health_check():

    return {
        "status": "healthy"
    }


# Customer query endpoint
@app.post("/ask")
def ask_question(query: CustomerQuery):

    return {
        "customer": query.customer_name,
        "question": query.question,
        "response": (
            "Thank you for contacting SupportIQ. "
            "We received your question."
        )
    }


# Create support ticket
@app.post("/tickets")
def create_ticket(ticket: TicketRequest):

    new_ticket = {
        "ticket_id": str(uuid4()),
        "customer_name": ticket.customer_name,
        "email": ticket.email,
        "complaint": ticket.complaint,
        "priority": classify_priority(ticket.complaint),
        "status": "Open",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        save_ticket(new_ticket)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to save ticket: {str(error)}"
        )

    return {
        "message": "Ticket created successfully",
        "ticket": new_ticket
    }


# Retrieve all tickets
@app.get("/tickets")
def get_all_tickets():

    tickets = db_get_all_tickets()

    return {
        "total_tickets": len(tickets),
        "tickets": tickets
    }


# Retrieve ticket using ticket ID
@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):

    ticket = get_ticket_by_id(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    return ticket


# Update ticket status
@app.patch("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: str,
    update: TicketStatusUpdate
):

    allowed_statuses = [
        "Open",
        "In Progress",
        "Resolved"
    ]

    if update.status not in allowed_statuses:

        raise HTTPException(
            status_code=400,
            detail="Invalid status. Choose Open, In Progress, or Resolved."
        )

    ticket = get_ticket_by_id(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    updated = db_update_ticket_status(
        ticket_id,
        update.status
    )

    if not updated:
        raise HTTPException(
            status_code=500,
            detail="Unable to update ticket status"
        )

    updated_ticket = get_ticket_by_id(ticket_id)

    return {
        "message": "Ticket status updated successfully",
        "ticket": updated_ticket
    }
