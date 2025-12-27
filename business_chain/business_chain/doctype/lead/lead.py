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
