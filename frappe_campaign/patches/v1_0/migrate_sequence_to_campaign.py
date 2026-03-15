import frappe

def execute():
	if not frappe.db.exists("DocType", "Sequence"):
		return
		
	# Migrate Sequences to Campaign
	sequences = frappe.get_all("Sequence", fields=["*"])
	
	for seq in sequences:
		if not frappe.db.exists("Campaign", {"campaign_name": seq.sequence_name}):
			campaign = frappe.new_doc("Campaign")
			campaign.campaign_name = seq.sequence_name
			campaign.description = getattr(seq, "description", "")
			campaign.apollo_ref_code = seq.apollo_ref_code
			
			steps = frappe.get_all("Sequence Step", filters={"parent": seq.name}, fields=["*"], order_by="idx asc")
			
			day_counter = 0
			for step in steps:
				if getattr(step, "type", "Auto Email") in ["Auto Email", "Manual Email"]:
					delay = getattr(step, "day_offset", 0)
					if delay is None:
						delay = 0
					day_counter += int(delay)
					campaign.append("campaign_schedules", {
						"email_template": step.get("email_template"),
						"send_after_days": day_counter
					})
					
			campaign.insert(ignore_permissions=True)

	# Migrate Sequence Contacts (if any) to Email Campaigns
	if frappe.db.exists("DocType", "Sequence Contact"):
		seq_contacts = frappe.get_all("Sequence Contact", fields=["*"])
		for sc in seq_contacts:
			# sequence -> campaign
			# reference_name -> recipient
			campaign_name = frappe.db.get_value("Sequence", sc.sequence, "sequence_name")
			
			recipient = sc.get("reference_name") or sc.get("crm_lead")
			
			if not campaign_name or not recipient:
				continue
				
			email_camp_name = frappe.db.get_value("Email Campaign", {"campaign_name": campaign_name, "recipient": recipient}, "name")
			if not email_camp_name:
				email_camp = frappe.new_doc("Email Campaign")
				email_camp.campaign_name = campaign_name
				email_camp.email_campaign_for = sc.get("reference_doctype") or "CRM Lead"
				email_camp.recipient = recipient
				email_camp.start_date = frappe.utils.today()
				
				# status mapping
				status_map = {
					"Draft": "",
					"Cold": "Scheduled",
					"Approaching": "In Progress",
					"Active": "In Progress",
					"Finished": "Completed",
					"Bounced": "Completed",
					"Opted Out": "Unsubscribed"
				}
				
				status_name = sc.status if sc.status else "Draft"
				email_camp.status = status_map.get(status_name, "")

				
				# Don't trigger standard creation logic so it doesn't send emails immediately
				email_camp.flags.ignore_validate = True
				email_camp.insert(ignore_permissions=True)
				email_camp_name = email_camp.name
				
			# Migrate Sequence Emails to Campaign Email Schedules
			if frappe.db.exists("DocType", "Sequence Email"):
				seq_emails = frappe.get_all("Sequence Email", filters={"sequence_contact": sc.name}, fields=["*"])
				if seq_emails:
					email_camp_doc = frappe.get_doc("Email Campaign", email_camp_name)
					changed = False
					for seq_email in seq_emails:
						step_idx = int(seq_email.step) if seq_email.step and str(seq_email.step).isdigit() else 1
						
						# Find matching schedule by idx
						for schedule in email_camp_doc.campaign_email_schedules:
							if schedule.idx == step_idx:
								if not schedule.subject and seq_email.subject:
									schedule.subject = seq_email.subject
									changed = True
								if not schedule.response and seq_email.message:
									schedule.response = seq_email.message
									changed = True
								break
					
					if changed:
						# If they are completed, make sure the overall status is correct
						if email_camp_doc.status in ["", None]:
							all_filled = all((s.subject and s.response) for s in email_camp_doc.get("campaign_email_schedules"))
							if all_filled:
								email_camp_doc.status = "Scheduled"
						
						email_camp_doc.flags.ignore_validate = True
						# We use db_update to avoid triggering webhooks repeatedly during migration
						email_camp_doc.db_update()
						for schedule in email_camp_doc.campaign_email_schedules:
							schedule.db_update()
