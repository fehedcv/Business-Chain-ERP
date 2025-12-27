import frappe

def after_insert(doc, method):
    # Only for managers
    if doc.role_in_unit != "Manager":
        return

    # Avoid duplicate permissions
    if frappe.db.exists(
        "User Permission",
        {
            "user": doc.user,
            "allow": "Business Unit",
            "for_value": doc.business_unit
        }
    ):
        return

    frappe.get_doc({
        "doctype": "User Permission",
        "user": doc.user,
        "allow": "Business Unit",
        "for_value": doc.business_unit,
        "apply_to_all_doctypes": 1
    }).insert(ignore_permissions=True)
