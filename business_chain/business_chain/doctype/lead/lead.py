# Copyright (c) 2025, vynx and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Lead(Document):

    '''def before_insert(self):
        frappe.throw("before_insert CALLED")
        """
        Rule 0: Always set source_agent automatically for Agents
        This is the single source of truth.
        """
        if "Agent" in frappe.get_roles():
            self.source_agent = frappe.session.user'''
    
    def after_insert(self):
        """
        Create provisional agent credit ledger entry
        when an agent creates a lead.
        """

        # ---- HARD GUARDS ----
        if not self.source_agent:
            return

        roles = frappe.get_roles(self.source_agent)
        if "Agent" not in roles:
            return

        # ---- PREVENT DUPLICATES ----
        exists = frappe.db.exists(
            "Agent Credit Ledger",
            {
                "lead": self.name,
                "transaction_type": "Credit"
            }
        )
        if exists:
            return

        ledger = frappe.new_doc("Agent Credit Ledger")
        ledger.agent = self.source_agent
        ledger.lead = self.name
        ledger.remarks = f"Provisional credit for lead of customer '{self.customer_name}'"

        # 🔑 SYSTEM FLAG (NOT A FIELD)
        ledger.flags.from_lead = True

        ledger.insert(ignore_permissions=True)


    def on_update(self):
        """
        Remove provisional credit if lead is rejected.
        """

        if self.status != "Rejected":
            return

        # ---- DELETE LEDGER ENTRY (IF EXISTS) ----
        ledger_name = frappe.db.get_value(
            "Agent Credit Ledger",
            {
                "lead": self.name,
                "transaction_type": "Credit"
            },
            "name"
        )

        if ledger_name:
            frappe.delete_doc(
                "Agent Credit Ledger",
                ledger_name,
                force=True
            )


    def validate(self):
        roles = frappe.get_roles()

        # Rule 1: Agents can ONLY create leads, never modify them
        if "Agent" in roles and not "System Manager" in roles and not self.is_new():
            frappe.throw("Agents are not allowed to modify leads after submission")

        # Rule 2: Only Business Managers can verify lead outcome
        if self.status in ("Converted", "Rejected"):
            if "Business_manager" not in roles and "System Manager" not in roles:
                frappe.throw("Only Business Managers can verify lead outcome")

        # Rule 3: Prevent tampering with source_agent
        if not self.is_new() and "Agent" in roles and not "System Manager" in roles:
            if self.source_agent != frappe.session.user:
                frappe.throw("You cannot change the source agent")


def get_permission_query_conditions(user):
    """
    Rule 4: Agents can ONLY see their own leads
    Enforced at database query level (Desk + API)
    """
    roles = frappe.get_roles(user)

    if "Agent" in roles:
        return f"`tabLead`.source_agent = '{user}'"

    return None
