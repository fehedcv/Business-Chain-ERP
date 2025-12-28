import frappe
from frappe import _
from business_chain.api.utils import get_owned_business_units

ALLOWED_STATUSES = [
    "Pending",
    "Verified",
    "In Progress",
    "Completed",
    "Rejected"
]

@frappe.whitelist()
def get_business_leads(status="All", search=None):
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if "Business_manager" not in roles and "System Manager" not in roles:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    owned_units = get_owned_business_units(user)

    if not owned_units:
        frappe.throw(_("No business unit access"))

    filters = {
        "business_unit": ["in", owned_units]
    }

    if status != "All":
        if status not in ALLOWED_STATUSES:
            frappe.throw(_("Invalid status"))
        filters["status"] = status

    if search:
        filters["client_name"] = ["like", f"%{search}%"]

    leads = frappe.get_all(
        "Lead",
        filters=filters,
        fields=[
            "name as id",
            "customer_name",
            "service",
            "status",
            "business_unit",
            "creation as date"
        ],
        order_by="creation desc"
    )
    

    # ---- SUMMARY COUNTS ----
    def count(status=None):
        f = {"business_unit": ["in", owned_units]}
        if status:
            f["status"] = status
        return frappe.db.count("Lead", f)

    summary = {
        "total": count(),
        "pending": count("Pending"),
        "verified": frappe.db.count(
            "Lead",
            {
                "business_unit": ["in", owned_units],
                "status": ["in", ["Verified", "In Progress", "Completed"]]
            }
        ),
        "in_progress": count("In Progress"),
        "completed": count("Completed"),
        "rejected": count("Rejected")
    }

    return {
        "summary": summary,
        "leads": leads
    }


@frappe.whitelist()
def update_lead_status(lead_id, status):
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if "Business_manager" not in roles and "System Manager" not in roles:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    lead = frappe.get_doc("Lead", lead_id)
    owned_units = get_owned_business_units(user)

    if lead.business_unit not in owned_units:
        frappe.throw(_("Unauthorized for this business unit"))

    transitions = {
        "Pending": ["Verified", "Rejected"],
        "Verified": ["In Progress"],
        "In Progress": ["Completed"]
    }

    if lead.status not in transitions or status not in transitions[lead.status]:
        frappe.throw(_("Invalid status transition"))

    lead.status = status
    lead.save(ignore_permissions=True)

    return {"success": True}



@frappe.whitelist()
def get_business_lead_detail(lead_id):
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if "Business_manager" not in roles and "System Manager" not in roles:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    lead = frappe.get_doc("Lead", lead_id)

    owned_units = get_owned_business_units(user)

    if lead.business_unit not in owned_units:
        frappe.throw(_("Unauthorized access to this lead"))

    return {
        "id": lead.name,
        "status": lead.status,
        "service": lead.service,
        "description": lead.description,
        "clientName": lead.customer_name,
        "clientPhone": lead.phone,
        
        "businessUnit": lead.business_unit,
        "agentId": lead.source_agent,
        "date": lead.creation
    }

@frappe.whitelist()
def submit_lead(
    business_unit: str,
    client_name: str,
    client_phone: str,
    service: str,
    notes: str = None
):
    """
    Agent submits a referral lead.
    """

    # ----------------------------
    # 1. AUTH & ROLE VALIDATION
    # ----------------------------
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if not user or user == "Guest":
        frappe.throw("Authentication required")

    if "Agent" not in roles:
        frappe.throw("Only agents can submit referrals")

    # ----------------------------
    # 2. BUSINESS UNIT VALIDATION
    # ----------------------------
    if not business_unit:
        frappe.throw("Business Unit is required")

    if not frappe.db.exists("Business Unit", business_unit):
        frappe.throw("Invalid Business Unit")

    # ----------------------------
    # 3. INPUT VALIDATION
    # ----------------------------
    if not client_name:
        frappe.throw("Client name is required")

    if not client_phone:
        frappe.throw("Client phone is required")

    if not service:
        frappe.throw("Service is required")

    # ----------------------------
    # 4. SERVICE NAME → ID RESOLUTION
    # ----------------------------
    service_id = frappe.db.get_value(
        "Business Unit Service",
        {"service_name": service},   # OR {"service_name": service} if that's your field
        "name"
    )

    if not service_id:
        frappe.throw(f"Invalid service: {service}")

    # ----------------------------
    # 5. CREATE LEAD (SERVER AUTHORITY)
    # ----------------------------
    lead = frappe.new_doc("Lead")
    lead.business_unit = business_unit
    lead.customer_name = client_name
    lead.client_phone = client_phone
    lead.service = service_id     # ✅ LINK FIELD GETS ID
    lead.notes = notes

    # 🔒 HARD RULES (NON-NEGOTIABLE)
    lead.source_agent = user
    lead.status = "Pending"
    lead.verified_by_admin = 0

    lead.insert(ignore_permissions=True)

    # ----------------------------
    # 6. RESPONSE
    # ----------------------------
    return {
        "lead_id": lead.name,
        "status": lead.status,
        "business_unit": business_unit
    }
