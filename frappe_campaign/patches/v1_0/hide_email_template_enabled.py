import frappe

def execute():
	if frappe.db.exists("Custom Field", "Email Template-enabled"):
		frappe.db.set_value("Custom Field", "Email Template-enabled", "hidden", 1)
