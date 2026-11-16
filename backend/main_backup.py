
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timezone

app = FastAPI(
    title="SupportIQ",
    description="AI Powered Customer Support Platform",
    version="1.0.0"
)

# Temporary ticket storage
tickets = []


# Customer query structure
class CustomerQuery(BaseModel):
    customer_name: str
    question: str


# Ticket creation structure
class TicketRequest(BaseModel):
    customer_name: str
    email: str
    complaint: str
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
    return {"status": "healthy"}


# Customer query endpoint
@app.post("/ask")
def ask_question(query: CustomerQuery):
    return {
        "customer": query.customer_name,
        "question": query.question,
        "response": "Thank you for contacting SupportIQ. We received your question."
    }


# Create support ticket
@app.post("/tickets")
def create_ticket(ticket: TicketRequest):

    ticket_id = str(uuid4())

    priority = classify_priority(ticket.complaint)

    new_ticket = {
        "ticket_id": ticket_id,
        "customer_name": ticket.customer_name,
        "email": ticket.email,
        "complaint": ticket.complaint,
        "priority": priority,
        "status": "Open",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    tickets.append(new_ticket)

    return {
        "message": "Ticket created successfully",
        "ticket": new_ticket
    }


# Retrieve all tickets
@app.get("/tickets")
def get_all_tickets():
    return {
        "total_tickets": len(tickets),
        "tickets": tickets
    }


# Retrieve ticket using ticket ID
@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):

    for ticket in tickets:

        if ticket["ticket_id"] == ticket_id:
            return ticket

    raise HTTPException(
        status_code=404,
        detail="Ticket not found"
    )
# Update ticket status
@app.patch("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: str,
    update: TicketStatusUpdate
):
    allowed_statuses = ["Open", "In Progress", "Resolved"]

    if update.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Choose Open, In Progress, or Resolved."
        )

    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            ticket["status"] = update.status

            return {
                "message": "Ticket status updated successfully",
                "ticket": ticket
            }

    raise HTTPException(
        status_code=404,
        detail="Ticket not found"
    )