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
            "creation as date",
            "source_agent",
            "payment_status",
            "credit_status"
        ],
        order_by="creation desc"
    )
    for lead in leads:
        service_name = frappe.get_value("Business Unit Service", lead.service, "service_name")
        lead["service"] = service_name if service_name else lead.service
        business_name = frappe.get_value("Business Unit", lead.business_unit, "business_name")
        lead["business_unit"] = business_name if business_name else lead.business_unit
        agent_name = frappe.get_value("User", lead.source_agent, "full_name")
        lead["agentId"] = agent_name if agent_name else lead.source_agent
        payment_status = lead.get("payment_status", "Pending")
        lead["paymentStatus"] = payment_status
        credit_status = lead.get("credit_status", "Pending")
        lead["creditStatus"] = credit_status



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

    #if lead is being marked as Verified, make a record in the Agent Credit Ledger with status Pending and credits 0, and reference to the lead
    if status == "Verified":
        ledger_entry = frappe.new_doc("Agent Credit Ledger")
        ledger_entry.agent = lead.source_agent
        ledger_entry.lead = lead.name
        ledger_entry.credits = 0
        ledger_entry.status = "Pending"
        ledger_entry.transaction_type = "Lead Reward"
        ledger_entry.remarks = f"Lead {lead.customer_name} marked as Verified - pending admin approval for credits"  
        ledger_entry.insert(ignore_permissions=True)

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
    agent_name = frappe.get_value("User", lead.source_agent, "full_name")
    agent_phone = frappe.get_value("User", lead.source_agent, "phone")
    #return commission percentage from the business unit doctype based on the business unit of the lead
    commission_pct = frappe.get_value("Business Unit", lead.business_unit, "commision")
    return {
        "id": lead.name,
        "status": lead.status,
        "service": frappe.get_value("Business Unit Service", lead.service, "service_name"),
        "description": lead.description,
        "clientName": lead.customer_name,
        "clientPhone": lead.phone,
        "businessUnit": frappe.get_value("Business Unit", lead.business_unit, "business_name"),
        "agentId": agent_name if agent_name else lead.source_agent,
        "date": lead.creation,
        "location": lead.custom_location,
        "agentPhone": agent_phone if agent_phone else "N/A",
        "commission": lead.approved_credits,
        "totalSaleAmount": lead.total_sale_amount,
        "paymentStatus": lead.payment_status,
        "commision": commission_pct
    }

@frappe.whitelist()
def submit_lead(
    business_unit: str,
    client_name: str,
    client_phone: str,
    service: str,
    notes: str = None,
    location: str = None,
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
        #business unit might be passed as its category 
        bu_name = frappe.db.get_value("Business Unit", {"category": business_unit}, "name")
        if not bu_name:
            frappe.throw("Invalid Business Unit")
        else:
            business_unit = bu_name
        

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
    #lead.phone should be converted to indian number format
    lead.phone = f"+91-{client_phone}"  # Ensure phone is a string
    lead.service = service_id     # ✅ LINK FIELD GETS ID
    lead.description = notes
    lead.custom_location = location

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



# api to settle agent credit. it will send commision and total sale amount of lead, update it in the doctype fields commision and total_sale_amount and change the status of the ledger entry to "Settled" and also update the remarks with the details of the settlement. only "System Manager" and "Business_manager" can perform this action, and only if the lead is in "Completed" status. it will also check if the ledger entry is in "Pending" status before settling.
@frappe.whitelist()
def settle_agent_credit(ledger_id, commission, total_sale_amount):
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if "Business_manager" not in roles and "System Manager" not in roles:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    lead = frappe.get_doc("Lead", ledger_id)

    if lead.payment_status != "Pending":
        frappe.throw(_("Only pending credits can be settled"))


    if lead.status != "Completed":
        frappe.throw(_("Can only settle credits for completed leads"))

    lead.approved_credits = commission
    lead.total_sale_amount = total_sale_amount
    lead.payment_status = "Settled"
    lead.remarks = f" | Settled with commission {commission} and total sale amount {total_sale_amount}"
    lead.credit_status = "Pending"
    lead.save(ignore_permissions=True)

    return {"success": True}