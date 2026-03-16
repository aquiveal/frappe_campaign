import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	"""
	Populates the 'campaigns' child table in CRM Lead with existing 
	Email Campaign records. Ensures the custom field exists first.
	"""
	
	# 1. Ensure the custom field exists in CRM Lead
	create_custom_fields({
		"CRM Lead": [
			{
				"fieldname": "campaigns",
				"fieldtype": "Table",
				"options": "CRM Lead Campaign",
				"label": "Campaigns",
				"hidden": 1,
				"module": "Campaign"
			}
		]
	})

	# 2. Fetch all unique pairs of Lead and Campaign
	email_campaigns = frappe.get_all(
		"Email Campaign",
		filters={"email_campaign_for": "CRM Lead"},
		fields=["recipient", "campaign_name"]
	)

	if not email_campaigns:
		return

	# 3. Iterate and update Leads
	updated_leads = set()
	for camp in email_campaigns:
		if frappe.db.exists("CRM Lead", camp.recipient):
			# Reload lead to ensure it has the new 'campaigns' field
			lead = frappe.get_doc("CRM Lead", camp.recipient)
			
			if not hasattr(lead, "campaigns"):
				continue

			# Check if entry already exists
			if not any(row.campaign_name == camp.campaign_name for row in lead.campaigns):
				lead.append("campaigns", {
					"campaign_name": camp.campaign_name
				})
				lead.save(ignore_permissions=True)
				updated_leads.add(camp.recipient)

	# 4. Clear cache for updated leads
	for lead_name in updated_leads:
		frappe.clear_cache(doctype="CRM Lead", name=lead_name)
	
	if updated_leads:
		frappe.clear_cache(doctype="CRM Lead")
