import frappe


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
@frappe.whitelist()
def get_agent_profile():
    agent = frappe.session.user
    agent_doc = frappe.get_doc("User", agent)
    return {
        "fullName": agent_doc.full_name,
        "phone": agent_doc.phone,
        "email": agent_doc.email,
        "profilePicture": agent_doc.user_image
    }   

#make an api that allows the agent to update their profile information such as full name, phone number and profile picture
@frappe.whitelist()
def update_agent_profile(full_name, phone, profile_picture):
    agent = frappe.session.user
    agent_doc = frappe.get_doc("User", agent)
    agent_doc.full_name = full_name
    agent_doc.phone = phone
    agent_doc.user_image = profile_picture
    agent_doc.save()
    return {
        "success": True,
        "message": "Profile updated successfully"
    }