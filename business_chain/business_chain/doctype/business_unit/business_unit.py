# Copyright (c) 2025, vynx and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BusinessUnit(Document):
	def after_insert(self):
		manager_email = self.email
		manager_name = self.manager_name
		business_unit_name = self.business_name

		if manager_email and manager_name:
			user = frappe.get_doc({
				"doctype": "User",
				"email": manager_email,
				"first_name": manager_name,
				"enabled": 1,
				"roles": [{"role": "Business_manager"}],
				"new_password": f"BU-{business_unit_name}-manager"
			})
			user.insert()

			frappe.get_doc({
				"doctype": "Business Unit Member",
				"business_unit": self.name,
				"user": user.name,
				"role_in_unit": "Manager"
			}).insert()
