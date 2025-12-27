import frappe
from frappe import _
from business_chain.api.utils import get_owned_business_units

@frappe.whitelist()
def get_my_business_unit():
    user = frappe.session.user

    owned_units = get_owned_business_units(user)
    if not owned_units:
        frappe.throw(_("No business unit access"))

    # For now: single primary unit
    unit = frappe.get_doc("Business Unit", owned_units[0])

    return {
        "id": unit.name,
        "name": unit.business_name,
        "website": unit.website,
        "email": unit.email,
        "contact": unit.primary_phone,
        "location": unit.location,
        "address": unit.address,
        "description": unit.description,
        "services": [
            {"name": s.service_name, "description": s.description}
            for s in unit.services
        ],
        "gallery": [g.image for g in unit.gallery]
    }


@frappe.whitelist()
def update_my_business_unit(data):
    import json

    if isinstance(data, str):
        data = json.loads(data)

    user = frappe.session.user

    unit_name = frappe.db.get_value(
        "Business Unit Member",
        {"user": user},
        "business_unit"
    )

    if not unit_name:
        frappe.throw("No business unit linked to this user")

    doc = frappe.get_doc("Business Unit", unit_name)

    doc.website = data.get("website")
    doc.email = data.get("email")
    doc.contact = data.get("contact")
    doc.location = data.get("location")
    doc.address = data.get("address")
    doc.description = data.get("description")

    doc.services = []
    for s in data.get("services", []):
        doc.append("services", {
            "service_name": s.get("name"),
            "description": s.get("description")
        })

    doc.gallery = []
    for g in data.get("gallery", []):
        doc.append("gallery", {"image": g})

    doc.save(ignore_permissions=True)

    return {"ok": True}

