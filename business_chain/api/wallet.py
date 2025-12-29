import frappe
from frappe.utils import formatdate

@frappe.whitelist()
def get_agent_wallet():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Authentication required")

    # Fetch ledger entries
    rows = frappe.get_all(
        "Agent Credit Ledger",
        filters={"agent": user},
        fields=[
            "name",
            "credits",
            "status",
            "transaction_type",
            "remarks",
            "creation"
        ],
        order_by="creation desc"
    )

    available = 0
    cleared = 0
    pending = 0

    ledger = []

    for r in rows:
        credits = r.credits or 0

        if credits > 0:
            available += credits
        else:
            cleared += abs(credits)



        ledger.append({
            "id": r.name,
            "credits": credits,
            "status": r.status,
            "type": r.transaction_type,
            "remarks": r.remarks,
            "date": r.creation.strftime("%d %b %Y")
        })

    return {
        "summary": {
            "available_cash": available - cleared ,   # ₹10 per credit
            "cleared_cash": cleared ,
            "credits_available": available 
        },
        "ledger": ledger
    }



def get_agent_available_credits(agent: str) -> int:
    """
    Returns the net available credits for an agent
    based purely on the Agent Credit Ledger.
    """

    if not agent:
        return 0

    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(credits), 0)
        FROM `tabAgent Credit Ledger`
        WHERE agent = %s
          AND status = 'Credited'
        """,
        (agent,),
    )

    return int(result[0][0] or 0)


@frappe.whitelist()
def request_withdrawal(requested_credits: int, remarks=None):
    user = frappe.session.user

    # --- AUTH ---
    if not user or user == "Guest":
        frappe.throw("Login required")

    if "Agent" not in frappe.get_roles(user):
        frappe.throw("Only agents can request withdrawals")

    if not requested_credits or requested_credits <= 0:
        frappe.throw("Invalid credit amount")

    # --- CHECK BALANCE ---
    available = get_agent_available_credits(user)
    if requested_credits > available:
        frappe.throw("Insufficient available credits")

    # --- CREATE WITHDRAWAL REQUEST ---
    req = frappe.new_doc("Agent Withdrawal Request")
    req.agent = user
    req.requested_credits = requested_credits
    req.status = "Pending"
    req.remarks = remarks
    req.insert(ignore_permissions=True)

    return {
        "request_id": req.name,
        "status": req.status
    }
