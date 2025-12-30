# Copyright (c) 2025, vynx and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AgentCreditLedger(Document):

    def validate(self):
        # ✅ Allow system-generated entries
        if getattr(self.flags, "ignore_validate", False):
            return
        
        if self.transaction_type in ("Lead Reward", "Withdrawal"):
            return

        # ✅ Allow Administrator explicitly
        if frappe.session.user == "Administrator":
            return

        # ❌ Block everything else
        frappe.throw("Only admin or system actions can create credit ledger entries")



def get_permission_query_conditions(user):
    roles = frappe.get_roles(user)

    # Rule 5: Agents can see ONLY their own ledger rows
    if "Agent" in roles:
        return f"`tabAgent Credit Ledger`.agent = '{user}'"

    return None
