import frappe

def execute():
	"""
	Populates the 'campaigns' child table in CRM Lead with existing 
	Email Campaign records.
	"""
	# 1. Fetch all unique pairs of Lead and Campaign
	email_campaigns = frappe.get_all(
		"Email Campaign",
		filters={"email_campaign_for": "CRM Lead"},
		fields=["recipient", "campaign_name"]
	)

	if not email_campaigns:
		return

	# 2. Iterate and update Leads
	updated_leads = set()
	for camp in email_campaigns:
		if frappe.db.exists("CRM Lead", camp.recipient):
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

	# Clear cache for updated leads
	for lead_name in updated_leads:
		frappe.clear_cache(doctype="CRM Lead", name=lead_name)
