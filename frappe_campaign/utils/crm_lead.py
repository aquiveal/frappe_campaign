import frappe

def sync_lead_campaign(doc, method):
	"""Update the hidden 'campaigns' child table on CRM Lead for filtering purposes"""
	if doc.email_campaign_for == "CRM Lead":
		if not frappe.db.exists("CRM Lead", doc.recipient):
			return

		lead = frappe.get_doc("CRM Lead", doc.recipient)
		
		if not hasattr(lead, "campaigns"):
			return

		# Check if already exists in child table
		if not any(row.campaign_name == doc.campaign_name for row in lead.campaigns):
			lead.append("campaigns", {
				"campaign_name": doc.campaign_name
			})
			lead.save(ignore_permissions=True)

def remove_lead_campaign(doc, method):
	"""Remove the reference from CRM Lead when an Email Campaign is deleted"""
	if doc.email_campaign_for == "CRM Lead":
		if not frappe.db.exists("CRM Lead", doc.recipient):
			return

		lead = frappe.get_doc("CRM Lead", doc.recipient)
		if not hasattr(lead, "campaigns"):
			return

		# Since we don't have the email_campaign link anymore, 
		# we should check if any OTHER email campaigns for this lead and campaign still exist
		other_exists = frappe.db.exists("Email Campaign", {
			"campaign_name": doc.campaign_name,
			"recipient": doc.recipient,
			"name": ("!=", doc.name)
		})

		if not other_exists:
			lead.set("campaigns", [
				row for row in lead.campaigns if row.campaign_name != doc.campaign_name
			])
			lead.save(ignore_permissions=True)
