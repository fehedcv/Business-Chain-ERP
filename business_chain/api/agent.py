import frappe
from frappe.utils.file_manager import save_file


@frappe.whitelist()
def get_agent_dashboard_data():
    if frappe.session.user == "Guest":
        frappe.throw(("You must be logged in to view dashboard data."), frappe.PermissionError)

    agent = frappe.session.user
    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(credits), 0)
        FROM `tabAgent Credit Ledger`
        WHERE agent = %s
          AND status = 'Approved'
        """,
        (agent,) 
    )
    result2 = frappe.db.sql(
        """
        SELECT COALESCE(SUM(credits), 0)
        FROM `tabAgent Credit Ledger`
        WHERE agent = %s
          AND status = 'Credited'
        """,
        (agent,) 
    )
    
    result3 = frappe.db.sql(
        """
        SELECT COALESCE(SUM(requested_credits), 0)
        FROM `tabAgent Withdrawal Request`
        WHERE agent = %s
          AND status = 'Pending'
        """,
        (agent,) 
    )

    wallet_balance = int(result[0][0] or 0) + int(result2[0][0] or 0) - int(result3[0][0] or 0)

    #add a variable to get the total payout credits for the agent from the Agent Credit Ledger with status Credited and return it as totalPayouts in the response
    result4 = frappe.db.sql(
        """
        SELECT COALESCE(SUM(credits), 0)
        FROM `tabAgent Credit Ledger`
        WHERE agent = %s
          AND status = 'Credited'
        """,
        (agent,)
    )
    total_payouts = int(result4[0][0] or 0)

    #add a variable called active leads to get the count of active leads for the agent from the Lead doctype where status is not in (Closed, Lost) and return it as activeLeads in the response
    result5 = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabLead`
        WHERE source_agent = %s
          AND status NOT IN ('Pending','Rejected','Completed')
        """,
        (agent,)
    )
    active_leads = int(result5[0][0] or 0)

    #add a variable called earning_activity to get the agent credit ledgers with status Approved or Credited and return it as earningActivity in the response
    earning_activity = frappe.db.sql(
        """
        SELECT credits, creation
        FROM `tabAgent Credit Ledger`
        WHERE agent = %s
          AND status IN ('Approved')
        ORDER BY creation DESC
        """,
        (agent,)
    )

    #add a variable called recent_activity to get the recent 5 leads and their status for the agent from the Lead doctype and return it as recentActivity in the response
    recent_activity = frappe.db.sql(
        """
        SELECT customer_name, status, creation
        FROM `tabLead`
        WHERE source_agent = %s
        ORDER BY creation DESC
        LIMIT 5
        """,
        (agent,)
    )


    return {
        "walletBalance": wallet_balance,
        "totalPayouts": total_payouts,
        "activeLeads": active_leads,
        "earningActivity": earning_activity,
        "recentActivity": recent_activity
    }


#make an api that returns the full name, phone number, email and profile picture of the agent based on the current logged in user

import frappe

@frappe.whitelist()
def get_agent_profile():
    user = frappe.session.user

    data = frappe.db.get_value(
        "Agent Profile",
        {"user": user},
        ["full_name", "phone", "pfp"],
        as_dict=True
    )

    if not data:
        frappe.throw("Agent profile not found")

    email = frappe.db.get_value("User", user, "email")

    return {
        "fullName": data.full_name,
        "phone": data.phone,
        "email": email,
        "profilePicture": data.pfp
    }

#make an api that allows the agent to update their profile information such as full name, phone number and profile picture
import frappe

@frappe.whitelist()
def update_agent_profile():
    data = frappe.form_dict

    full_name = data.get("full_name")
    phone = data.get("phone")
    profile_picture = data.get("profile_picture")

    if not full_name:
        frappe.throw("Full name is required")

    user = frappe.session.user

    # 1. Get Agent Profile
    profile_name = frappe.db.get_value("Agent Profile", {"user": user})

    if not profile_name:
        frappe.throw("Agent profile not found")

    profile = frappe.get_doc("Agent Profile", profile_name)

    # 2. Update profile fields ONLY
    profile.full_name = full_name.strip()

    if phone:
        profile.phone = phone

    if profile_picture:
        if not profile_picture.startswith("/files/"):
            frappe.throw("Invalid profile picture path")
        profile.pfp = profile_picture

    profile.save(ignore_permissions=True)

    return {
        "success": True,
        "message": "Profile updated successfully"
    }

@frappe.whitelist()
def upload_profile_picture():
    if 'file' not in frappe.request.files:
        frappe.throw("No file uploaded")

    uploaded_file = frappe.request.files['file']

    file_doc = save_file(
        fname=uploaded_file.filename,
        content=uploaded_file.read(),
        dt="Agent Profile",   # optional link
        dn=frappe.session.user,
        is_private=0
    )

    agent = frappe.session.user
    profile_name = frappe.db.get_value("Agent Profile", {"user": agent})

    if not profile_name:
        frappe.throw("Agent profile not found")

    profile = frappe.get_doc("Agent Profile", profile_name)
    profile.pfp = file_doc.file_url
    profile.save(ignore_permissions=True)


    return {
        "success": True,
        "fileUrl": file_doc.file_url
    }