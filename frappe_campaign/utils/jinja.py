import frappe

def get_sequence_message(lead_name, sequence_name, step, test):
    """
    Fetches the email body for the specified sequence and step.
    """
    # 1. Find the Sequence Contact record
    # Note: Assuming 'reference_name' stores the Lead ID
    seq_contact = frappe.db.get_value("Sequence Contact",
        {"reference_name": lead_name, "sequence": sequence_name},
        "name"
    )
    
    if not seq_contact:
        return ""

    # 2. Fetch the content linked to this sequence contact and step
    content = frappe.db.get_value("Sequence Email",
        {"sequence_contact": seq_contact, "step": step, "test": test},
        "message"
    )
    
    return content or ""
