
import io
import sys
import csv
import requests
import streamlit as st

from pathlib import Path
from datetime import datetime
from uuid import uuid4


# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database

database.create_table()

API_URL = "http://127.0.0.1:8000"

APP_VERSION = "3.0.0"

# ==========================================
# AUTO-START BACKEND IF RUNNING IN CLOUD
# ==========================================

import socket
import threading
import time

@st.cache_resource
def ensure_backend_online():
    # Check if port 8000 is already active
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(('127.0.0.1', 8000)) == 0:
                return True
    except Exception:
        pass

    def run_uvicorn():
        import uvicorn
        from backend.main import app as fastapi_app
        uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="error")

    t = threading.Thread(target=run_uvicorn, daemon=True)
    t.start()
    time.sleep(1.5)
    return True

ensure_backend_online()

st.set_page_config(
    page_title="SupportIQ",
    page_icon="🎧",
    layout="wide"
)


# ==========================================
# 2. PRIORITY CLASSIFICATION
# ==========================================

def classify_priority(complaint):

    complaint = complaint.lower()

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

    if any(word in complaint for word in high_keywords):
        return "High"

    elif any(word in complaint for word in medium_keywords):
        return "Medium"

    return "Low"


# ==========================================
# 3. DATABASE OPERATIONS
# ==========================================

def load_tickets():
    return database.get_all_tickets()


def create_ticket(customer_name, email, complaint):

    ticket = {
        "ticket_id": str(uuid4()),
        "customer_name": customer_name.strip(),
        "email": email.strip(),
        "complaint": complaint.strip(),
        "priority": classify_priority(complaint),
        "status": "Open",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "category": None,
        "sentiment": None,
        "suggested_response": None,
        "ai_analyzed": 0
    }

    database.save_ticket(ticket)

    return ticket


# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================

def count_values(tickets, field, value):
    return sum(
        ticket.get(field) == value
        for ticket in tickets
    )


PRIORITY_BADGE = {
    "High": "🔴",
    "Medium": "🟠",
    "Low": "🟢"
}

STATUS_BADGE = {
    "Open": "🟡",
    "In Progress": "🔵",
    "Resolved": "✅"
}


def display_ticket(ticket, show_delete=False):

    priority = ticket.get("priority", "Low")
    status = ticket.get("status", "Open")
    p_icon = PRIORITY_BADGE.get(priority, "")
    s_icon = STATUS_BADGE.get(status, "")

    with st.container(border=True):

        header_col, badge_col = st.columns([3, 1])

        with header_col:
            st.markdown(
                f"### {ticket.get('customer_name', 'Unknown Customer')}"
            )

        with badge_col:
            st.markdown(
                f"**{p_icon} {priority}** &nbsp; {s_icon} {status}",
                unsafe_allow_html=True
            )

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Email:**", ticket.get("email", "N/A"))
            st.write("**Priority:**", f"{p_icon} {priority}")
            st.write("**Status:**", f"{s_icon} {status}")

            if ticket.get("category"):
                st.write("**Category:**", ticket["category"])

            if ticket.get("sentiment"):
                st.write("**Sentiment:**", ticket["sentiment"])

        with col2:
            st.write("**Ticket ID:**")
            st.code(ticket.get("ticket_id", "N/A"))
            st.write(
                "**AI Analysed:**",
                "✅ Yes" if ticket.get("ai_analyzed") == 1 else "❌ No"
            )

        st.write("**Customer Complaint:**")
        st.write(ticket.get("complaint", "N/A"))

        if ticket.get("suggested_response"):
            with st.expander("💬 View AI Suggested Response"):
                st.write(ticket["suggested_response"])

        footer_col, delete_col = st.columns([3, 1])

        with footer_col:
            st.caption(
                f"Created: {ticket.get('created_at', 'N/A')}"
            )

        if show_delete:
            with delete_col:
                if st.button(
                    "🗑️ Delete",
                    key=f"delete_{ticket['ticket_id']}",
                    type="secondary"
                ):
                    deleted = database.delete_ticket(ticket["ticket_id"])
                    if deleted:
                        st.success("Ticket deleted.")
                        st.rerun()
                    else:
                        st.error("Could not delete ticket.")


def show_progress_breakdown(title, data):

    st.markdown(f"### {title}")

    maximum = max(data.values(), default=0)

    for label, count in data.items():

        col1, col2 = st.columns([1, 3])

        with col1:
            st.write(f"**{label}**")
            st.caption(f"{count} ticket(s)")

        with col2:
            st.progress(
                count / maximum if maximum > 0 else 0.0
            )


def validate_customer(customer_name, email, complaint):

    if not customer_name.strip():
        return "Please enter the customer name."

    if (
        not email.strip()
        or "@" not in email
        or "." not in email.split("@")[-1]
    ):
        return "Please enter a valid email address."

    if not complaint.strip():
        return "Please enter the customer complaint."

    return None


def tickets_to_csv(tickets):

    if not tickets:
        return ""

    export_cols = [
        "ticket_id",
        "customer_name",
        "email",
        "complaint",
        "priority",
        "status",
        "category",
        "sentiment",
        "ai_analyzed",
        "suggested_response",
        "created_at"
    ]

    # Only keep columns that actually exist in the data

    sample = tickets[0] if tickets else {}
    cols = [c for c in export_cols if c in sample]

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=cols,
        extrasaction="ignore",
        lineterminator="\n"
    )
    writer.writeheader()

    for ticket in tickets:
        row = {k: ticket.get(k, "") for k in cols}
        row["ai_analyzed"] = "Yes" if row.get("ai_analyzed") == 1 else "No"
        writer.writerow(row)

    return output.getvalue()


# ==========================================
# 5. SIDEBAR NAVIGATION
# ==========================================

st.sidebar.title("🎧 SupportIQ")

st.sidebar.caption(
    "AI-Powered Customer Support Platform"
)

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard",
        "🎫 Create Ticket",
        "📋 All Tickets",
        "🤖 AI Analysis",
        "📤 Export Data"
    ]
)

st.sidebar.divider()

st.sidebar.info(
    "Manage customer complaints and support tickets."
)

st.sidebar.divider()

# Live backend status indicator

try:
    health = requests.get(f"{API_URL}/health", timeout=2)
    if health.status_code == 200:
        st.sidebar.success("🟢 Backend: Online")
    else:
        st.sidebar.warning("🟡 Backend: Degraded")
except Exception:
    st.sidebar.error("🔴 Backend: Offline")

st.sidebar.caption(
    f"Powered by FastAPI · Streamlit · Llama 3.2  \n"
    f"Version {APP_VERSION}"
)


# ==========================================
# 6. DASHBOARD
# ==========================================

if page == "📊 Dashboard":

    st.title("📊 SupportIQ Dashboard")

    st.write(
        "Monitor customer support performance and AI insights."
    )

    tickets = load_tickets()

    # --------------------------------------
    # TICKET STATISTICS
    # --------------------------------------

    total = len(tickets)

    open_count = count_values(tickets, "status", "Open")

    progress_count = count_values(
        tickets, "status", "In Progress"
    )

    resolved_count = count_values(
        tickets, "status", "Resolved"
    )

    high_count = count_values(tickets, "priority", "High")

    medium_count = count_values(tickets, "priority", "Medium")

    low_count = count_values(tickets, "priority", "Low")

    ai_tickets = [
        ticket for ticket in tickets
        if ticket.get("ai_analyzed") == 1
    ]

    # --------------------------------------
    # MAIN KPI CARDS
    # --------------------------------------

    st.subheader("📈 Support Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Tickets", total)
    col2.metric("🟡 Open", open_count)
    col3.metric("🔵 In Progress", progress_count)
    col4.metric("✅ Resolved", resolved_count)

    st.divider()

    # --------------------------------------
    # PRIORITY OVERVIEW
    # --------------------------------------

    st.subheader("🚦 Ticket Priority Overview")

    p1, p2, p3 = st.columns(3)

    p1.metric("🔴 High Priority", high_count)
    p2.metric("🟠 Medium Priority", medium_count)
    p3.metric("🟢 Low Priority", low_count)

    st.divider()

    # --------------------------------------
    # STATUS + PRIORITY VISUALIZATION
    # --------------------------------------

    vis_col1, vis_col2 = st.columns(2)

    with vis_col1:
        status_data = {
            "Open": open_count,
            "In Progress": progress_count,
            "Resolved": resolved_count
        }
        show_progress_breakdown(
            "📌 Ticket Status Distribution",
            status_data
        )

    with vis_col2:
        priority_data = {
            "High": high_count,
            "Medium": medium_count,
            "Low": low_count
        }
        show_progress_breakdown(
            "🚦 Priority Distribution",
            priority_data
        )

    st.divider()

    # --------------------------------------
    # AI COMPLAINT ANALYTICS
    # --------------------------------------

    st.subheader("🤖 AI Complaint Analytics")

    ai_pct = (
        f"{round(len(ai_tickets) / total * 100)}%"
        if total > 0 else "N/A"
    )

    ai_col1, ai_col2 = st.columns(2)
    ai_col1.metric("AI Analysed Tickets", len(ai_tickets))
    ai_col2.metric("AI Analysis Rate", ai_pct)

    if ai_tickets:

        category_col, sentiment_col = st.columns(2)

        categories = [
            "Payment", "Refund", "Delivery",
            "Account", "Technical Support", "Other"
        ]

        sentiments = ["Positive", "Negative", "Neutral"]

        category_data = {
            category: count_values(ai_tickets, "category", category)
            for category in categories
        }

        sentiment_data = {
            sentiment: count_values(ai_tickets, "sentiment", sentiment)
            for sentiment in sentiments
        }

        with category_col:
            show_progress_breakdown(
                "Complaint Categories",
                category_data
            )

        with sentiment_col:
            show_progress_breakdown(
                "Customer Sentiment",
                sentiment_data
            )

    else:

        st.info(
            "No AI-analysed tickets yet. Use the **AI Analysis** page to get started."
        )

    st.divider()

    # --------------------------------------
    # RECENT TICKETS
    # --------------------------------------

    st.subheader("📋 Recent Tickets")

    if tickets:

        sorted_tickets = sorted(
            tickets,
            key=lambda t: t.get("created_at", ""),
            reverse=True
        )

        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "Open", "In Progress", "Resolved"],
                key="dashboard_status"
            )

        with filter_col2:
            priority_filter = st.selectbox(
                "Filter by Priority",
                ["All", "High", "Medium", "Low"],
                key="dashboard_priority"
            )

        filtered = sorted_tickets

        if status_filter != "All":
            filtered = [t for t in filtered if t.get("status") == status_filter]

        if priority_filter != "All":
            filtered = [t for t in filtered if t.get("priority") == priority_filter]

        st.caption(f"Showing {len(filtered)} matching ticket(s)")

        if filtered:
            for ticket in filtered[:5]:
                display_ticket(ticket)

            if len(filtered) > 5:
                st.info(
                    f"Showing 5 of {len(filtered)} tickets. "
                    "Go to **All Tickets** to see the full list."
                )

        else:
            st.warning("No tickets match the selected filters.")

    else:
        st.info("No tickets yet. Create your first ticket!")

    if st.button("🔄 Refresh Dashboard"):
        st.rerun()


# ==========================================
# 7. CREATE TICKET
# ==========================================

elif page == "🎫 Create Ticket":

    st.title("🎫 Create Support Ticket")

    st.write("Register a new customer complaint manually.")

    with st.form("create_ticket_form"):

        customer_name = st.text_input(
            "Customer Name",
            placeholder="Enter customer name"
        )

        email = st.text_input(
            "Email Address",
            placeholder="Enter email address"
        )

        complaint = st.text_area(
            "Customer Complaint",
            placeholder="Describe the customer's issue...",
            height=120
        )

        submitted = st.form_submit_button(
            "✅ Create Ticket",
            use_container_width=True
        )

    if submitted:

        error_message = validate_customer(
            customer_name, email, complaint
        )

        if error_message:
            st.error(error_message)

        else:

            try:

                ticket = create_ticket(
                    customer_name, email, complaint
                )

                st.success("✅ Ticket created successfully!")

                st.subheader("Ticket Details")

                d1, d2 = st.columns(2)

                with d1:
                    st.write("**Customer:**", ticket["customer_name"])
                    st.write("**Email:**", ticket["email"])
                    st.write("**Priority:**",
                             f"{PRIORITY_BADGE.get(ticket['priority'], '')} {ticket['priority']}")
                    st.write("**Status:**", ticket["status"])

                with d2:
                    st.write("**Ticket ID:**")
                    st.code(ticket["ticket_id"])
                    st.write("**Created:**", ticket["created_at"])

                st.info(
                    "💡 Use **AI Analysis** to get category, sentiment and a suggested response."
                )

            except Exception as error:
                st.error(f"Unable to create ticket: {error}")


# ==========================================
# 8. ALL TICKETS
# ==========================================

elif page == "📋 All Tickets":

    st.title("📋 All Support Tickets")

    st.write("Search, filter, update and manage customer tickets.")

    tickets = load_tickets()

    if not tickets:
        st.info("No tickets found. Create a ticket first.")

    else:

        # ----------------------------------
        # SEARCH
        # ----------------------------------

        search = st.text_input(
            "🔍 Search by customer name, email, ticket ID or complaint"
        )

        # ----------------------------------
        # FILTERS
        # ----------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "Open", "In Progress", "Resolved"],
                key="all_status"
            )

        with col2:
            priority_filter = st.selectbox(
                "Filter by Priority",
                ["All", "High", "Medium", "Low"],
                key="all_priority"
            )

        with col3:
            ai_filter = st.selectbox(
                "Filter by AI Analysis",
                ["All", "AI Analysed", "Not AI Analysed"],
                key="all_ai"
            )

        # ----------------------------------
        # APPLY FILTERS
        # ----------------------------------

        filtered_tickets = tickets.copy()

        if search:

            search_text = search.lower()

            filtered_tickets = [
                t for t in filtered_tickets
                if (
                    search_text in t.get("customer_name", "").lower()
                    or search_text in t.get("email", "").lower()
                    or search_text in t.get("ticket_id", "").lower()
                    or search_text in t.get("complaint", "").lower()
                )
            ]

        if status_filter != "All":
            filtered_tickets = [
                t for t in filtered_tickets
                if t.get("status") == status_filter
            ]

        if priority_filter != "All":
            filtered_tickets = [
                t for t in filtered_tickets
                if t.get("priority") == priority_filter
            ]

        if ai_filter == "AI Analysed":
            filtered_tickets = [
                t for t in filtered_tickets
                if t.get("ai_analyzed") == 1
            ]
        elif ai_filter == "Not AI Analysed":
            filtered_tickets = [
                t for t in filtered_tickets
                if t.get("ai_analyzed") != 1
            ]

        sorted_tickets = sorted(
            filtered_tickets,
            key=lambda t: t.get("created_at", ""),
            reverse=True
        )

        st.write(f"Showing **{len(sorted_tickets)}** ticket(s)")

        if sorted_tickets:
            for ticket in sorted_tickets:
                display_ticket(ticket, show_delete=True)
        else:
            st.warning("No tickets match your search or filters.")

        st.divider()

        # ----------------------------------
        # UPDATE TICKET STATUS
        # ----------------------------------

        st.subheader("🔁 Update Ticket Status")

        all_ticket_ids = [t["ticket_id"] for t in tickets]

        selected_id = st.selectbox(
            "Select Ticket ID",
            all_ticket_ids,
            format_func=lambda tid: next(
                (
                    f"{t['customer_name']} — {tid[:8]}..."
                    for t in tickets if t["ticket_id"] == tid
                ),
                tid
            )
        )

        new_status = st.selectbox(
            "Select New Status",
            ["Open", "In Progress", "Resolved"]
        )

        if st.button("✅ Update Status", type="primary"):

            try:
                updated = database.update_ticket_status(
                    selected_id, new_status
                )

                if updated:
                    st.success("Ticket status updated successfully!")
                    st.rerun()

                else:
                    st.error("Ticket not found.")

            except Exception as error:
                st.error(f"Unable to update status: {error}")


# ==========================================
# 9. AI COMPLAINT ANALYSIS
# ==========================================

elif page == "🤖 AI Analysis":

    st.title("🤖 AI Complaint Analysis")

    st.write(
        "Analyse customer complaints using **Llama 3.2** running locally via Ollama."
    )

    with st.expander("ℹ️ How it works"):
        st.markdown(
            """
            1. Enter the customer's details and complaint below.
            2. The complaint is sent to your **FastAPI backend** at `http://127.0.0.1:8000`.
            3. The backend forwards it to **Ollama (Llama 3.2:3b)** running locally.
            4. The AI returns a **category**, **sentiment**, **priority** and a **suggested response**.
            5. A support ticket is automatically saved to the database.

            > ⚠️ Make sure both the FastAPI backend and Ollama are running before using this page.
            """
        )

    with st.form("ai_analysis_form"):

        customer_name = st.text_input(
            "Customer Name",
            placeholder="Enter customer name"
        )

        email = st.text_input(
            "Email Address",
            placeholder="Enter customer email"
        )

        complaint = st.text_area(
            "Customer Complaint",
            placeholder="Describe the customer's problem...",
            height=120
        )

        submitted = st.form_submit_button(
            "🤖 Analyse Complaint",
            use_container_width=True
        )

    if submitted:

        error_message = validate_customer(
            customer_name, email, complaint
        )

        if error_message:
            st.error(error_message)

        else:

            payload = {
                "customer_name": customer_name.strip(),
                "email": email.strip(),
                "complaint": complaint.strip()
            }

            response = None

            try:

                with st.spinner(
                    "🤖 Llama 3.2 is analysing the complaint... (may take up to 60 s)"
                ):

                    response = requests.post(
                        f"{API_URL}/ai/analyze",
                        json=payload,
                        timeout=180
                    )

                    response.raise_for_status()

                    result = response.json()

                analysis = result["ai_analysis"]
                ticket = result["ticket"]

                # --------------------------
                # SUCCESS MESSAGE
                # --------------------------

                st.success(
                    "✅ AI analysis completed and support ticket created!"
                )

                st.divider()

                # --------------------------
                # AI ANALYSIS RESULTS
                # --------------------------

                st.subheader("🧠 AI Analysis Results")

                col1, col2, col3 = st.columns(3)

                col1.metric("📂 Category", analysis["category"])
                col2.metric("💬 Sentiment", analysis["sentiment"])
                col3.metric(
                    "🚦 Priority",
                    f"{PRIORITY_BADGE.get(analysis['priority'], '')} {analysis['priority']}"
                )

                st.divider()

                # --------------------------
                # SUGGESTED RESPONSE
                # --------------------------

                st.subheader("💬 Suggested Customer Response")

                st.info(analysis["suggested_response"])

                st.divider()

                # --------------------------
                # CREATED TICKET
                # --------------------------

                st.subheader("🎫 Automatically Created Support Ticket")

                st.success("Ticket saved to database successfully!")

                st.write("**Ticket ID:**")
                st.code(ticket["ticket_id"])

                ticket_col1, ticket_col2 = st.columns(2)

                with ticket_col1:
                    st.write("**Customer:**", ticket["customer_name"])
                    st.write("**Email:**", ticket["email"])
                    st.write("**Category:**", ticket["category"])

                with ticket_col2:
                    st.write("**Priority:**", ticket["priority"])
                    st.write("**Sentiment:**", ticket["sentiment"])
                    st.write("**Status:**", ticket["status"])

                st.caption(
                    "This ticket is now visible in the **All Tickets** section."
                )

            except requests.exceptions.HTTPError as error:

                try:
                    error_details = response.json().get(
                        "detail", str(error)
                    )
                except (ValueError, AttributeError):
                    error_details = str(error)

                st.error(f"Backend error: {error_details}")

            except requests.exceptions.ConnectionError:

                st.error(
                    "❌ Could not connect to the backend. "
                    "Make sure the FastAPI server is running:\n\n"
                    "```\nuvicorn backend.main:app --reload\n```"
                )

            except requests.exceptions.Timeout:

                st.error(
                    "⏱️ The AI model took too long to respond. "
                    "Ollama may be loading the model. Please try again."
                )

            except requests.exceptions.RequestException as error:
                st.error(f"Request error: {error}")

            except (KeyError, ValueError, TypeError):
                st.error(
                    "The backend returned an unexpected response. "
                    "Check that the FastAPI server is up to date."
                )

            except Exception as error:
                st.error(f"Unexpected error: {error}")


# ==========================================
# 10. EXPORT DATA
# ==========================================

elif page == "📤 Export Data":

    st.title("📤 Export Data")

    st.write(
        "Download your support tickets as a CSV file for reporting or analysis."
    )

    tickets = load_tickets()

    if not tickets:

        st.info(
            "No tickets to export. Create some tickets first."
        )

    else:

        # ----------------------------------
        # EXPORT FILTERS
        # ----------------------------------

        st.subheader("🔧 Export Options")

        exp_col1, exp_col2, exp_col3 = st.columns(3)

        with exp_col1:
            exp_status = st.selectbox(
                "Filter by Status",
                ["All", "Open", "In Progress", "Resolved"],
                key="exp_status"
            )

        with exp_col2:
            exp_priority = st.selectbox(
                "Filter by Priority",
                ["All", "High", "Medium", "Low"],
                key="exp_priority"
            )

        with exp_col3:
            exp_ai = st.selectbox(
                "Filter by AI Analysis",
                ["All", "AI Analysed", "Not AI Analysed"],
                key="exp_ai"
            )

        # Apply filters

        export_tickets = tickets.copy()

        if exp_status != "All":
            export_tickets = [
                t for t in export_tickets
                if t.get("status") == exp_status
            ]

        if exp_priority != "All":
            export_tickets = [
                t for t in export_tickets
                if t.get("priority") == exp_priority
            ]

        if exp_ai == "AI Analysed":
            export_tickets = [
                t for t in export_tickets
                if t.get("ai_analyzed") == 1
            ]
        elif exp_ai == "Not AI Analysed":
            export_tickets = [
                t for t in export_tickets
                if t.get("ai_analyzed") != 1
            ]

        st.write(
            f"**{len(export_tickets)}** ticket(s) will be exported."
        )

        # ----------------------------------
        # PREVIEW TABLE
        # ----------------------------------

        if export_tickets:

            st.subheader("📋 Preview")

            preview_cols = [
                "ticket_id",
                "customer_name",
                "email",
                "priority",
                "status",
                "category",
                "sentiment",
                "ai_analyzed",
                "created_at"
            ]

            sample = export_tickets[0] if export_tickets else {}
            cols = [c for c in preview_cols if c in sample]

            preview_slice = export_tickets[:20]
            if len(export_tickets) > 20:
                st.caption(f"Showing preview of first 20 of {len(export_tickets)} tickets.")

            # Render HTML table (avoids Streamlit st.table pandas dependency)
            table_header = "".join(
                f"<th style='padding: 10px 12px; border-bottom: 2px solid #555; text-align: left;'>"
                f"{c.replace('_', ' ').title()}</th>"
                for c in cols
            )
            table_rows = []
            for t in preview_slice:
                cells = []
                for c in cols:
                    val = t.get(c, "")
                    if c == "ai_analyzed":
                        val = "Yes" if val == 1 else "No"
                    elif c == "ticket_id" and val:
                        val = f"<code>{str(val)[:8]}...</code>"
                    cells.append(f"<td style='padding: 8px 12px; border-bottom: 1px solid rgba(128,128,128,0.2);'>{val}</td>")
                table_rows.append(f"<tr>{''.join(cells)}</tr>")

            html_table = f"""
            <div style="overflow-x: auto; margin-bottom: 20px; border-radius: 6px; border: 1px solid rgba(128,128,128,0.2);">
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead><tr>{table_header}</tr></thead>
                    <tbody>{''.join(table_rows)}</tbody>
                </table>
            </div>
            """
            st.markdown(html_table, unsafe_allow_html=True)

            # ----------------------------------
            # DOWNLOAD BUTTON
            # ----------------------------------

            csv_data = tickets_to_csv(export_tickets)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"supportiq_tickets_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

        else:

            st.warning(
                "No tickets match the selected filters."
            )

        st.divider()

        # ----------------------------------
        # DATABASE SUMMARY
        # ----------------------------------

        st.subheader("📊 Database Summary")

        total = len(tickets)
        ai_count = sum(1 for t in tickets if t.get("ai_analyzed") == 1)
        open_count = sum(1 for t in tickets if t.get("status") == "Open")
        resolved_count = sum(1 for t in tickets if t.get("status") == "Resolved")

        sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)

        sum_col1.metric("Total Tickets", total)
        sum_col2.metric("AI Analysed", ai_count)
        sum_col3.metric("Open", open_count)
        sum_col4.metric("Resolved", resolved_count)
