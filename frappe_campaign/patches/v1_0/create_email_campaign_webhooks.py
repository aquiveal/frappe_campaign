import frappe

def execute():
	create_generation_webhook()
	create_dispatcher_webhook()

def create_generation_webhook():
	if frappe.db.exists("Webhook", {"name": "Email Campaign Generation"}):
		return

	# Webhook URL normally comes from site config, but for the document, we use a placeholder if not set
	generation_endpoint = frappe.conf.get("n8n_generation_webhook_url") or "http://your-n8n-url/webhook/generate-email"

	webhook = frappe.new_doc("Webhook")
	webhook.name = "Email Campaign Generation"
	webhook.webhook_doctype = "Email Campaign"
	webhook.webhook_docevent = "on_update"
	webhook.request_url = generation_endpoint

	webhook.condition = "doc.status in ['', None]"
	
	webhook.webhook_json = """{
  "event": "EmailCampaign.GenerationRequested",
  "email_campaign": "{{ doc.name }}"
}"""
	webhook.insert(ignore_permissions=True)

def create_dispatcher_webhook():
	if frappe.db.exists("Webhook", {"name": "Email Campaign Dispatcher"}):
		return

	dispatcher_endpoint = frappe.conf.get("n8n_apollo_dispatcher_url") or "http://your-n8n-url/webhook/dispatch-apollo"

	webhook = frappe.new_doc("Webhook")
	webhook.name = "Email Campaign Dispatcher"
	webhook.webhook_doctype = "Email Campaign"
	webhook.webhook_docevent = "on_update"
	webhook.condition = "doc.status == 'Scheduled'"
	webhook.request_url = dispatcher_endpoint
	
	webhook.webhook_json = """{
  "event": "EmailCampaign.DispatchRequested",
  "email_campaign": "{{ doc.name }}"
}"""
	webhook.insert(ignore_permissions=True)
