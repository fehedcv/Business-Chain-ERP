# Copyright (c) 2025, vynx and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AgentCreditLedger(Document):

    def validate(self):
        roles = frappe.get_roles()

        # Rule 1: Only Admin can create ledger entries
        if self.is_new() and "System Manager" not in roles:
            frappe.throw("Only admin can create credit ledger entries")

        # Rule 2: Credits cannot be zero
        if self.credits == 0:
            frappe.throw("Credits cannot be zero")

        # Rule 3: Lead Reward must reference a Lead
        if self.transaction_type == "Lead Reward" and not self.lead:
            frappe.throw("Lead Reward must be linked to a Lead")

        # Rule 4: Prevent edits to existing ledger rows (extra safety)
        if not self.is_new():
            frappe.throw("Ledger entries cannot be modified")


def get_permission_query_conditions(user):
    roles = frappe.get_roles(user)

    # Rule 5: Agents can see ONLY their own ledger rows
    if "Agent" in roles:
        return f"`tabAgent Credit Ledger`.agent = '{user}'"

    return None
