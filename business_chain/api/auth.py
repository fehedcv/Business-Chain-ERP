import frappe
from frappe.utils.password import update_password

@frappe.whitelist(allow_guest=True)
def agent_signup(full_name, email, password, phone):
    if frappe.db.exists("User", email):
        frappe.throw("An account with this email already exists.")

    parts = full_name.strip().split(" ", 1)
    user = frappe.get_doc({
        "doctype":           "User",
        "email":             email,
        "first_name":        parts[0],
        "last_name":         parts[1] if len(parts) > 1 else "",
        "full_name":         full_name,
        "phone":         phone,
        "send_welcome_email": 0,
        "enabled":           1,
    })
    user.append("roles", {"role": "Agent"})
    user.insert(ignore_permissions=True)
    update_password(email, password)
    frappe.db.commit()

    return {"status": "ok"}