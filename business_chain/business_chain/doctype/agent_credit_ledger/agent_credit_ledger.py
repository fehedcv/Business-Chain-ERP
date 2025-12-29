# Copyright (c) 2025, vynx and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AgentCreditLedger(Document):

    def validate(self):
        # Allow system actions
        if self.transaction_type in ("Lead Reward", "Withdrawal"):
            return

        # Block manual creation
        if frappe.session.user != "Administrator":
            frappe.throw("Only admin can create credit ledger entries")

    #def validate(self):
       # ✅ Allow system-created ledger entries
        '''if self.flags.get("from_lead"):
            return'''



def get_permission_query_conditions(user):
    roles = frappe.get_roles(user)

    # Rule 5: Agents can see ONLY their own ledger rows
    if "Agent" in roles:
        return f"`tabAgent Credit Ledger`.agent = '{user}'"

    return None
