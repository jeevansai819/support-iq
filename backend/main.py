
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timezone
import requests
import json

from database import (
    create_table,
    save_ticket,
    get_all_tickets as db_get_all_tickets,
    get_ticket_by_id,
    update_ticket_status as db_update_ticket_status,
    delete_ticket as db_delete_ticket
)


# --------------------------------
# APPLICATION CONFIGURATION
# --------------------------------

app = FastAPI(
    title="SupportIQ",
    description="AI-Powered Customer Support Platform",
    version="3.0.0"
)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

create_table()


# --------------------------------
# REQUEST MODELS
# --------------------------------

class CustomerQuery(BaseModel):
    customer_name: str
    question: str


class TicketRequest(BaseModel):
    customer_name: str
    email: str
    complaint: str


class TicketStatusUpdate(BaseModel):
    status: str


# --------------------------------
# PRIORITY CLASSIFICATION
# --------------------------------

def classify_priority(complaint):
    text = complaint.lower()

    high_keywords = [
        "fraud",
        "hacked",
        "account compromised",
        "security breach",
        "unauthorized transaction",
        "payment failed",
        "money deducted",
        "double payment",
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

    return "Low"


# --------------------------------
# HOME ENDPOINT
# --------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to SupportIQ!",
        "status": "Application is running"
    }


# --------------------------------
# HEALTH ENDPOINT
# --------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# --------------------------------
# CUSTOMER QUERY ENDPOINT
# --------------------------------

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


# --------------------------------
# CREATE SUPPORT TICKET
# --------------------------------

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


# --------------------------------
# GET ALL SUPPORT TICKETS
# --------------------------------

@app.get("/tickets")
def get_all_tickets():

    tickets = db_get_all_tickets()

    return {
        "total_tickets": len(tickets),
        "tickets": tickets
    }


# --------------------------------
# GET INDIVIDUAL TICKET
# --------------------------------

@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):

    ticket = get_ticket_by_id(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    return ticket


# --------------------------------
# UPDATE TICKET STATUS
# --------------------------------

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


# --------------------------------
# DELETE TICKET
# --------------------------------

@app.delete("/tickets/{ticket_id}")
def delete_ticket(ticket_id: str):

    ticket = get_ticket_by_id(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    deleted = db_delete_ticket(ticket_id)

    if not deleted:
        raise HTTPException(
            status_code=500,
            detail="Unable to delete ticket"
        )

    return {
        "message": "Ticket deleted successfully",
        "ticket_id": ticket_id
    }


# --------------------------------
# AI COMPLAINT ANALYSIS + TICKET CREATION
# --------------------------------

@app.post("/ai/analyze")
def analyze_complaint(ticket: TicketRequest):

    prompt = f"""
You are an expert customer support analyst.

Analyze the customer complaint carefully.

CUSTOMER NAME:
{ticket.customer_name}

CUSTOMER COMPLAINT:
{ticket.complaint}

TASK 1: CATEGORY

Select exactly ONE category:

Payment
Refund
Delivery
Account
Technical Support
Other

Category guidelines:

Payment: Failed transactions, deducted money,
payment errors and transaction problems.

Refund: Refund requests, delayed refunds and
money that has not been returned.

Delivery: Late, missing or damaged orders.

Account: Login, password and account access problems.

Technical Support: Software errors, application
problems and technical failures.

Other: Issues that do not match the categories above.

TASK 2: SENTIMENT

Select exactly ONE:

Positive
Negative
Neutral

TASK 3: PRIORITY

Select exactly ONE:

High
Medium
Low

Priority guidelines:

High: Fraud, hacked accounts, security threats,
unauthorized transactions and urgent financial risks.

Medium: Refund delays, payment problems,
delivery delays and unresolved service issues.

Low: General questions and non-urgent enquiries.

TASK 4: CUSTOMER RESPONSE

Write a polite, professional and empathetic response.

Address the customer by their first name when appropriate.
Acknowledge their actual complaint.
Ask for relevant information if needed.
Do not promise refunds or actions that have not been verified.

IMPORTANT RULES:

- Return exactly one category.
- Return exactly one sentiment.
- Return exactly one priority.
- Never return the list of available options.
- Do not invent customer or transaction information.
- Return only valid JSON.
- Do not include Markdown or code fences.

Use exactly this JSON structure:

{{
    "category": "Refund",
    "sentiment": "Negative",
    "priority": "Medium",
    "suggested_response": "Write a professional response here."
}}
"""

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1
                }
            },
            timeout=180
        )

        response.raise_for_status()

        result = response.json()
        ai_text = result.get("response", "")

        analysis = json.loads(ai_text)

        # Validate AI response structure

        required_fields = [
            "category",
            "sentiment",
            "priority",
            "suggested_response"
        ]

        for field in required_fields:
            if field not in analysis:
                raise ValueError(
                    f"Missing AI response field: {field}"
                )

        # Validate classification values

        allowed_categories = [
            "Payment",
            "Refund",
            "Delivery",
            "Account",
            "Technical Support",
            "Other"
        ]

        allowed_sentiments = [
            "Positive",
            "Negative",
            "Neutral"
        ]

        allowed_priorities = [
            "High",
            "Medium",
            "Low"
        ]

        if analysis["category"] not in allowed_categories:
            raise ValueError("Invalid AI category")

        if analysis["sentiment"] not in allowed_sentiments:
            raise ValueError("Invalid AI sentiment")

        if analysis["priority"] not in allowed_priorities:
            raise ValueError("Invalid AI priority")

        if (
            not isinstance(analysis["suggested_response"], str)
            or not analysis["suggested_response"].strip()
        ):
            raise ValueError("Invalid AI suggested response")

        # Create ticket using AI analysis

        new_ticket = {
            "ticket_id": str(uuid4()),
            "customer_name": ticket.customer_name,
            "email": ticket.email,
            "complaint": ticket.complaint,
            "priority": analysis["priority"],
            "status": "Open",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "category": analysis["category"],
            "sentiment": analysis["sentiment"],
            "suggested_response": analysis["suggested_response"],
            "ai_analyzed": 1
        }

        # Save ticket to SQLite

        try:
            save_ticket(new_ticket)

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"AI analysis succeeded, but ticket could not be saved: {str(error)}"
            )

        return {
            "message": "AI analysis completed and ticket created successfully",
            "customer_name": ticket.customer_name,
            "email": ticket.email,
            "complaint": ticket.complaint,
            "ai_analysis": analysis,
            "ticket": new_ticket
        }

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="AI model took too long to respond. Please try again."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to Ollama. Check whether Ollama is running."
        )

    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="AI returned an invalid response. Please try again."
        )
