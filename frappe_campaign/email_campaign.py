import frappe
from frappe import _
import json

@frappe.whitelist()
def get(name=None, filters=None):
	"""
	Highly efficient endpoint for n8n to fetch all context in a single network request.
	Returns the exact Email Campaign document structure, but with the 'recipient' 
	field enriched to contain the full CRM Lead, Organization, and FCRM Notes.
	Accepts either 'name' directly, or standard Frappe 'filters'.
	"""
	if filters:
		if isinstance(filters, str):
			filters = json.loads(filters)
			
		matched_campaigns = frappe.get_all("Email Campaign", filters=filters, pluck="name", limit=1)
		if not matched_campaigns:
			frappe.throw(_("Email Campaign not found matching filters"), frappe.DoesNotExistError)
		name = matched_campaigns[0]
			
	if not name:
		frappe.throw(_("Please provide name or filters"), frappe.ValidationError)
		
	campaign = frappe.get_doc("Email Campaign", name)
	payload = campaign.as_dict()
	
	if campaign.email_campaign_for == "CRM Lead":
		lead = frappe.get_doc("CRM Lead", campaign.recipient)
		
		# Replace the string ID with the enriched object
		payload["recipient"] = {
			"name": campaign.recipient,
			"first_name": lead.first_name,
			"last_name": getattr(lead, "last_name", ""),
			"email": getattr(lead, "email", ""),
			"fcrm_notes": frappe.get_all(
				"FCRM Note", 
				filters={"reference_doctype": "CRM Lead", "reference_docname": campaign.recipient}, 
				pluck="content"
			),
			"organization": None
		}
		
		# Organization Data
		if getattr(lead, "organization", None):
			org = frappe.get_doc("CRM Organization", lead.organization)
			
			payload["recipient"]["organization"] = {
				"name": org.name,
				"website": getattr(org, "website", ""),
				"fcrm_notes": frappe.get_all(
					"FCRM Note", 
					filters={"reference_doctype": "CRM Organization", "reference_docname": lead.organization}, 
					pluck="content"
				)
			}
			
	return payload

@frappe.whitelist()
def update(name, schedules):
	"""
	API for n8n to update email schedules.
	Only accepts updates if status is empty (needs generation).
	"""
	campaign = frappe.get_doc("Email Campaign", name)
	
	if campaign.status not in ["", None, "Draft"]:
		# Ignore retry requests if already generated or failed to prevent Convoy from getting stuck in a retry loop
		return {"status": "ignored", "reason": "Campaign status is already {0}".format(campaign.status)}
	
	if isinstance(schedules, str):
		schedules = json.loads(schedules)
		
	for s_data in schedules:
		for s in campaign.campaign_email_schedules:
			if s.name == s_data.get("name"):
				s.subject = s_data.get("subject")
				s.response = s_data.get("response")
				break
	
	campaign.save(ignore_permissions=True)
	return {"status": "success"}
