import frappe

def get_owned_business_units(user):
    """
    Returns list of business units where user is an owner
    """
    return frappe.get_all(
        "Business Unit Member",
        filters={
            "user": user,
            "role_in_unit": "Manager"
        },
        pluck="business_unit"
    )
