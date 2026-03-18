import frappe
from frappe import _
import json
from markdownify import markdownify as md

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
	
	# Prepare Jinja Context (kept separate from payload so n8n only gets rendered prompts)
	context = payload.copy()
	
	if campaign.email_campaign_for == "CRM Lead":
		lead = frappe.get_doc("CRM Lead", campaign.recipient)
		
		recipient_data = lead.as_dict()
		recipient_data["fcrm_notes"] = frappe.get_all(
			"FCRM Note", 
			filters={"reference_doctype": "CRM Lead", "reference_docname": campaign.recipient}, 
			fields=["*"]
		)
		recipient_data["organization"] = None
		
		# Organization Data
		if getattr(lead, "organization", None):
			organizaton = frappe.get_doc("CRM Organization", lead.organization)
			
			organizaton_data = organizaton.as_dict()
			organizaton_data["fcrm_notes"] = frappe.get_all(
				"FCRM Note", 
				filters={"reference_doctype": "CRM Organization", "reference_docname": lead.organization}, 
				fields=["*"]
			)
			recipient_data["organization"] = organizaton_data
			
		context.update(recipient_data)
		context["recipient"] = recipient_data # Keep it available via {{ recipient.first_name }} too

	# Process Email Schedules
	for schedule in payload.get("campaign_email_schedules", []):
		if schedule.get("email_template"):
			template_doc = frappe.get_doc("Email Template", schedule["email_template"])
			template_dict = template_doc.as_dict()

			# Render prompts if they exist
			if template_dict.get("user_prompt"):
				rendered_html = frappe.render_template(template_dict["user_prompt"], context)
				template_dict["user_prompt"] = md(rendered_html).strip()
			
			if template_dict.get("system_prompt"):
				rendered_html = frappe.render_template(template_dict["system_prompt"], context)
				template_dict["system_prompt"] = md(rendered_html).strip()
			
			# Replace the string ID with the fully enriched template object
			schedule["email_template"] = template_dict

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
