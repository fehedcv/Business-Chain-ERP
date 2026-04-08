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


@frappe.whitelist()
def get_team_data():
    if frappe.session.user != "Administrator":
        frappe.throw(("You must be logged in to view dashboard data."), frappe.PermissionError)

    '''
    required api endpoint example response:
    {
  "agents": [
    {
      "name": "AGT-001",
      "full_name": "Zaid Al-Farsi",
      "email": "zaid.f@vynx.com",
      "phone": "+971 50 123 4567",
      "creation": "2025-10-12 00:00:00",
      "status": "Active",
      "wallet_balance": 1250
    }
  ],
  "leads": [
    {
      "name": "LEAD-001",
      "customer_name": "Faisal Tharammal",
      "status": "Verified",
      "source_agent": "AGT-001"
    }
  ]
}
    '''
    agents = frappe.db.sql(
        """        SELECT name, full_name, email, phone, creation, enabled
        FROM `tabUser`
        WHERE name IN (SELECT parent FROM `tabHas Role` WHERE role = 'Agent')
        """,
        as_dict=True
    )
    for agent in agents:
        result = frappe.db.sql(
            """
            SELECT COALESCE(SUM(credits), 0)
            FROM `tabAgent Credit Ledger`
            WHERE agent = %s
              AND status = 'Approved'
            """,
            (agent.name,) 
        )
        result2 = frappe.db.sql(
            """
            SELECT COALESCE(SUM(credits), 0)
            FROM `tabAgent Credit Ledger`
            WHERE agent = %s
              AND status = 'Credited'
            """,
            (agent.name,) 
        )
        
        result3 = frappe.db.sql(
            """
            SELECT COALESCE(SUM(requested_credits), 0)
            FROM `tabAgent Withdrawal Request`
            WHERE agent = %s
              AND status = 'Pending'
            """,
            (agent.name,) 
        )

        wallet_balance = int(result[0][0] or 0) + int(result2[0][0] or 0) - int(result3[0][0] or 0)
        agent.wallet_balance = wallet_balance
    leads = frappe.db.sql(
        """        SELECT name, customer_name, status, source_agent
        FROM `tabLead`
        """,
        as_dict=True
    )

    return {
        "agents": agents,
        "leads": leads
    }
@frappe.whitelist()
def get_credit_settlement_data():
    """
    Returns all data needed by the CreditSettlement React component in one call:
    - Leads with payment_status = "Pending", enriched with BU/service display names
    - All Agent Withdrawal Requests
    """

    user = frappe.session.user
    if user != "Administrator":
        frappe.throw(("You must be logged in to view this data."), frappe.PermissionError)

    # ── 1. Fetch leads with pending payment status ─────────────────────────────
    leads_raw = frappe.get_all(
        "Lead",
        filters={"credit_status": "Pending"},
        fields=[
            "name", "customer_name", "phone", "email",
            "custom_location", "business_unit", "service",
            "description", "status", "source_agent",
            "total_sale_amount", "approved_credits",
            "verified_by_admin", "verification_notes",
            "payment_status", "remarks", "creation",
        ],
        order_by="creation desc",
    )

    # ── 2. Fetch all Business Units ────────────────────────────────────────────
    business_units = frappe.get_all(
        "Business Unit",
        fields=["name", "business_name", "commision"],
    )

    bu_map = {bu["name"]: bu for bu in business_units}

    # ── 3. Fetch all service rows ──────────────────────────────────────────────
    service_rows = frappe.get_all(
        "Business Unit Service",
        fields=["name", "service_name", "parent"],
        order_by="idx asc",
    )

    service_map = {}
    for row in service_rows:
        if row.get("name"):
            service_map[row["name"]] = row["service_name"]
        if row.get("service_name"):
            service_map[row["service_name"]] = row["service_name"]

    # ── 4. Enrich leads with computed financial fields ─────────────────────────
    leads = []
    for lead in leads_raw:
        bu_id = lead.get("business_unit", "")
        bu_doc = bu_map.get(bu_id, {})
        commission_pct = bu_doc.get("commision", 10)

        total = lead.get("total_sale_amount") or 0
        commission_amount = total * (commission_pct / 100)
        agent_credit = lead.get("approved_credits") or commission_amount
    #add ledgerId to the lead dictionary with the value of the name field of the Agent Credit Ledger entry linked to the lead, if exists, else set it to None. you can find the linked Agent Credit Ledger entry by filtering on the Lead field in the Agent Credit Ledger doctype with the name of the lead
        ledger_entry = frappe.db.get_value(
            "Agent Credit Ledger",
            filters={"lead": lead["name"]},
            fieldname="name"
        )
        lead["ledgerId"] = ledger_entry if ledger_entry else None

        leads.append({
            "id":                  lead["name"],
            "client_name":         lead.get("customer_name", "—"),
            "client_phone":        lead.get("phone", ""),
            "client_address":      lead.get("custom_location", ""),
            "description":         lead.get("description", ""),
            "lead_status":         lead.get("status", ""),
            "agent_name":          lead.get("source_agent") or "System",
            "agent_id":            lead.get("source_agent") or "VYNX-CORE",
            "date":                lead["creation"].strftime("%Y-%m-%d") if lead.get("creation") else "—",
            # Resolved display names
            "business_unit":       bu_doc.get("business_name", bu_id or "—"),
            "service":             service_map.get(lead.get("service", ""), lead.get("service", "—")),
            # Financial
            "total_sale_amount":   total,
            "commission_pct":      commission_pct,
            "commission_amount":   commission_amount,
            "agent_credit":        agent_credit,
            # Payment
            "payment_status":      lead.get("payment_status", ""),
            "remarks":             lead.get("remarks", ""),
            "verified_by_admin":   lead.get("verified_by_admin", 0),
            "verification_notes":  lead.get("verification_notes", ""),
            "ledger_id":           lead.get("ledgerId", None)
        })

    # ── 5. Fetch withdrawal requests ───────────────────────────────────────────
    withdrawals = frappe.get_all(
        "Agent Withdrawal Request",
        fields=["name", "agent", "requested_credits", "status", "remarks", "requested_on"],
        order_by="requested_on desc",
    )

    return {
        "leads":       leads,
        "withdrawals": withdrawals,
    }