# Copyright (c) 2025, vynx and contributors
# For license information, please see license.txt

# Copyright (c) 2025, vynx and contributors

import frappe
from frappe.model.document import Document
from business_chain.api.wallet import get_agent_available_credits 

class AgentWithdrawalRequest(Document):

    def on_update(self):
        self._create_ledger_on_credit()

    def _create_ledger_on_credit(self):
        doc_before_save = self.get_doc_before_save()

        # Only act on transition to "Credited" status
        if not (self.status == "Credited" and doc_before_save and doc_before_save.status != "Credited"):
            return

        if self.requested_credits > get_agent_available_credits(self.agent):
            frappe.throw("Insufficient available credits")
            return

        # --- CREATE NEGATIVE LEDGER ENTRY ---
        ledger = frappe.new_doc("Agent Credit Ledger")
        ledger.agent = self.agent
        ledger.lead = None  # withdrawals are not tied to leads
        ledger.credits = -abs(self.requested_credits)
        ledger.status = "Credited"
        ledger.transaction_type = "Withdrawal"
        ledger.remarks = f"Withdrawal credited via request {self.name}"
        # Mark as system-generated (IMPORTANT)
        ledger.flags.ignore_validate = True
        ledger.insert(ignore_permissions=True)
