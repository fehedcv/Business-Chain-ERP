import frappe

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
