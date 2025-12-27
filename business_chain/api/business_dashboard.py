import frappe
from frappe.utils import getdate, add_days, nowdate


@frappe.whitelist()
def get_business_overview():
    """
    Returns aggregated dashboard data for the logged-in Business Manager.
    Backend-enforced. No frontend filtering required.
    """

    user = frappe.session.user
    roles = frappe.get_roles(user)

    # ---- AUTH GUARD ----
    if "Business_manager" not in roles and "System Manager" not in roles:
        frappe.throw("Not permitted", frappe.PermissionError)

    # ---- FETCH LEADS (already permission-filtered by Frappe) ----
    leads = frappe.get_all(
        "Lead",
        fields=["name", "status", "creation"],
    )

    # ---- STATUS COUNTS ----
    stats = {
        "total": 0,
        "verified": 0,
        "in_progress": 0,
        "completed": 0,
        "rejected": 0,
    }

    for lead in leads:
        stats["total"] += 1

        status = (lead.status or "").lower()

        if status == "verified":
            stats["verified"] += 1
        elif status == "in progress":
            stats["in_progress"] += 1
        elif status == "completed":
            stats["completed"] += 1
        elif status == "rejected":
            stats["rejected"] += 1

    # ---- COMPLETION RATE ----
    completion_rate = (
        round((stats["completed"] / stats["total"]) * 100)
        if stats["total"] > 0
        else 0
    )

    # ---- LAST 7 DAYS TREND (by creation date) ----
    today = getdate(nowdate())
    last_7_days = [add_days(today, -i) for i in range(6, -1, -1)]

    trend_map = {d: 0 for d in last_7_days}

    for lead in leads:
        created = getdate(lead.creation)
        if created in trend_map:
            trend_map[created] += 1

    trend = {
        "labels": [d.strftime("%d/%m") for d in last_7_days],
        "data": [trend_map[d] for d in last_7_days],
    }

    # ---- FINAL PAYLOAD ----
    return {
        **stats,
        "completion_rate": completion_rate,
        "trend": trend,
    }
