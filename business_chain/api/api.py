import frappe
from frappe.utils import formatdate

@frappe.whitelist()
def whoami():
    user = frappe.session.user

    if user == "Guest":
        frappe.throw("Not logged in", frappe.PermissionError)

    roles = frappe.get_roles(user)

    if "System Manager" in roles:
        primary_role = "admin"
    elif "Business_manager" in roles:
        primary_role = "business"
    elif "Agent" in roles:
        primary_role = "agent"
    else:
        primary_role = "unknown"

    return {
        "user": user,
        "roles": roles,
        "primary_role": primary_role
    }


@frappe.whitelist()
def get_business_unit(business_unit: str):
    """
    Fetch a single Business Unit with services and gallery.
    Used by Agent & Business dashboards.
    """

    if not business_unit:
        frappe.throw("Business Unit is required")

    # 1️⃣ Fetch Business Unit
    if frappe.db.exists("Business Unit", business_unit):
        bu = frappe.get_doc("Business Unit", business_unit)
    else:
        # allow lookup by ID if needed later
        bu = frappe.get_all(
            "Business Unit",
            filters={"name": business_unit},
            limit=1
        )
        if not bu:
            frappe.throw("Business Unit not found")
        bu = frappe.get_doc("Business Unit", bu[0].name)

    # 2️⃣ Normalize child tables
    services = [
        {
            "name": s.service_name,
            "description": s.description
        }
        for s in bu.services or []
    ]

    gallery = [img.image for img in bu.gallery or []]

    # 3️⃣ Response payload (frontend-safe)
    return {
        "id": bu.name,
        "name": bu.business_name or bu.name,
        "website": bu.website,
        "email": bu.email,
        "contact": bu.primary_phone,
        "location": bu.location,
        "address": bu.address,
        "description": bu.description,
        "services": services,
        "gallery": gallery
    }



@frappe.whitelist()
def get_my_lead_history():
    """
    Returns all leads submitted by the logged-in agent
    """

    user = frappe.session.user
    roles = frappe.get_roles(user)

    if not user or user == "Guest":
        frappe.throw("Authentication required")

    if "Agent" not in roles:
        frappe.throw("Only agents can view this")

    leads = frappe.get_all(
        "Lead",
        filters={
            "source_agent": user
        },
        fields=[
            "customer_name",
            "business_unit",
            "status",
            "creation"
        ],
        order_by="creation desc"
    )

    result = []
    i=1
    for l in leads:
        result.append({
            "id": i,
            "clientName": l.customer_name,
            "businessUnit": frappe.get_value("Business Unit", l.business_unit, "business_name"),
            "status": normalize_status(l.status),
            "date": formatdate(l.creation)
        })
        i+=1

    return result


def normalize_status(status):
    """
    UI-level normalization
    """
    if status in ("Verified", "Completed"):
        return "Successful"
    if status == "Rejected":
        return "Rejected"
    return "Pending"
