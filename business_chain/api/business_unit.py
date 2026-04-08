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
            {"id": s.name, "name": s.service_name, "description": s.description}
            for s in unit.services
        ],
        "gallery": [g.image for g in unit.gallery],
        "logo": unit.logo or "",
        "commision": unit.commision,
        "facebook": unit.facebook,
        "instagram": unit.instagram,
        "linkedin": unit.linkedin
    }
@frappe.whitelist()
def update_my_business_unit(patch):
    if isinstance(patch, str):
        patch = json.loads(patch)

    user = frappe.session.user
    unit_name = frappe.db.get_value(
        "Business Unit Member", {"user": user}, "business_unit"
    )
    if not unit_name:
        frappe.throw("No business unit linked to this user")

    doc = frappe.get_doc("Business Unit", unit_name)

    # ── Scalar fields (only update keys that are present in the patch) ──────
    scalar_map = {
        "website":     "website",
        "contact":     "contact",
        "location":    "location",
        "address":     "address",
        "description": "description",
        "instagram":   "instagram",
        "facebook":    "facebook",
        "linkedin":    "linkedin",
    }
    for patch_key, doc_field in scalar_map.items():
        if patch_key in patch:
            setattr(doc, doc_field, patch[patch_key])

    # ── Services (partial upsert + delete) ───────────────────────────────────
    if "services" in patch:
        svc_patch = patch["services"]

        # Delete removed rows by child docname
        deleted_ids = svc_patch.get("deleted_ids", [])
        if deleted_ids:
            doc.services = [r for r in doc.services if r.name not in deleted_ids]

        # Upsert modified/new rows
        existing_by_id = {r.name: r for r in doc.services}
        for s in svc_patch.get("upserted", []):
            row_id = s.get("id")
            if row_id and row_id in existing_by_id:
                # Update in place — preserves row order and docname
                row = existing_by_id[row_id]
                row.service_name = s.get("name", row.service_name)
                row.description  = s.get("description", row.description)
            else:
                # New row
                doc.append("services", {
                    "service_name": s.get("name", ""),
                    "description":  s.get("description", ""),
                })

    # ── Gallery (add new URLs, remove deleted ones) ──────────────────────────
    if "gallery" in patch:
        gal_patch  = patch["gallery"]
        removed_set = set(gal_patch.get("removed", []))

        if removed_set:
            doc.gallery = [r for r in doc.gallery if r.image not in removed_set]

        for url in gal_patch.get("added", []):
            doc.append("gallery", {"image": url})

    doc.save(ignore_permissions=True)
    return {"ok": True}

@frappe.whitelist()
def upload_business_unit_logo():
    user = frappe.session.user
    owned_units = get_owned_business_units(user)
    if not owned_units:
        frappe.throw(_("No business unit access"))
    
    unit_name = owned_units[0]
    
    # Upload the file using Frappe's handler
    from frappe.handler import upload_file
    file_doc = upload_file()
    
    # Now explicitly set it on the document
    doc = frappe.get_doc("Business Unit", unit_name)
    doc.logo = file_doc.file_url
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {"file_url": file_doc.file_url}