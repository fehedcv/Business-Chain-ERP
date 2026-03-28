import frappe

@frappe.whitelist()
def get_admin_dashboard_data():
    if frappe.session.user != "Administrator":
        frappe.throw(("You must be logged in to view dashboard data."), frappe.PermissionError)

    # return inquiry generated in the last 30 days, day by day, as a list of dictionaries with keys date and count
    daily_activity = frappe.db.sql(
        """        SELECT DATE(creation) as date, COUNT(*) as count
        FROM `tabLead`
        WHERE creation >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY DATE(creation)
        ORDER BY DATE(creation) ASC
        """,
        as_dict=True
    )

    #return number of inquiry in status pending, verified and completed
    inquiry_pending = frappe.db.sql(
        """        SELECT COUNT(*) as count
        FROM `tabLead`
        WHERE status = 'Pending'
        """,
        as_dict=True
    )
    inquiry_verified = frappe.db.sql(
        """        SELECT COUNT(*) as count
        FROM `tabLead`
        WHERE status = 'Verified'
        """,
        as_dict=True
    )
    inquiry_completed = frappe.db.sql(
        """        SELECT COUNT(*) as count
        FROM `tabLead`
        WHERE status = 'Completed'
        """,
        as_dict=True
    )  

    #return 3 top performing business units based on the number of leads generated in the last 30 days, as a list of dictionaries with keys business_unit and lead_count
    top_business_units = frappe.db.sql(
        """        SELECT business_unit, COUNT(*) as lead_count
        FROM `tabLead`
        WHERE creation >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY business_unit
        ORDER BY lead_count DESC
        LIMIT 3
        """,
        as_dict=True
    )

    #return total number of leads generated in the last 30 days
    total_leads = frappe.db.sql(
        """        SELECT COUNT(*) as count
        FROM `tabLead`
        WHERE creation >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """,
        as_dict=True
    )

    #return total number of business units
    total_business_units = frappe.db.sql(
        """        SELECT COUNT(*) as count
        FROM `tabBusiness Unit`
        """,
        as_dict=True
    )

    #return total number of users with the role "Agent"
    total_agents = frappe.db.sql(
        """        SELECT COUNT(*) as count
        FROM `tabUser`
        WHERE name IN (SELECT parent FROM `tabHas Role` WHERE role = 'Agent')
        """,
        as_dict=True
    )

    all_agents = frappe.db.sql(
        """        SELECT name, full_name, email, phone
        FROM `tabUser`
        WHERE name IN (SELECT parent FROM `tabHas Role` WHERE role = 'Agent')
        """,
        as_dict=True
    )


    all_business_units = frappe.db.sql(
        """        SELECT name, business_name, category
        FROM `tabBusiness Unit`
        """,
        as_dict=True
    )


    return {
        "inquiryGenerated": daily_activity,
        "inquiryPending": inquiry_pending[0].count,
        "inquiryVerified": inquiry_verified[0].count,
        "inquiryCompleted": inquiry_completed[0].count,
        "topBusinessUnits": top_business_units,
        "allBusinessUnits": all_business_units,
        "totalLeads": total_leads[0].count,
        "totalBusinessUnits": total_business_units[0].count,
        "totalAgents": total_agents[0].count,
        "allAgents": all_agents
    }


