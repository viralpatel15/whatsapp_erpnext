import json
import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import get_safe_globals, safe_exec
from frappe.integrations.utils import make_post_request
from frappe.desk.form.utils import get_pdf_link
from frappe.utils.background_jobs import enqueue


def validate(self, method):
	if self.channel == "WhatsApp":
		fields = frappe.get_doc("DocType", self.document_type).fields
		fields += frappe.get_all(
			"Custom Field",
			filters={"dt": self.document_type},
			fields=["fieldname"]
		)
		# if not any(field.fieldname == self.custom_receiver_mobile for field in fields): # noqa
		# 	frappe.throw(f"Field name {self.custom_receiver_mobile} does not exists")
		
def on_trash(self, method):
	pass
	# if self.channel == "WhatsApp":
	# 	if self.notification_type == "Scheduler Event":
	# 		frappe.delete_doc("Scheduled Job Type", self.name)

	# 	frappe.cache().delete_value("whatsapp_notification_map")

def after_insert(self, method):
	pass
	# if self.channel == "WhatsApp":
	# 	if self.notification_type == "Scheduler Event":
	# 		method = f"whatsapp_erpnext.utils.trigger_whatsapp_notifications_{self.event_frequency.lower().replace(' ', '_')}" # noqa
	# 		job = frappe.get_doc(
	# 			{
	# 				"doctype": "Scheduled Job Type",
	# 				"method": method,
	# 				"frequency": self.event_frequency
	# 			}
	# 		)

	# 		job.insert()

def format_number(self, number):
	if (number.startswith("+")):
		number = number[1:len(number)]

	return number

def send_scheduled_message(self) -> dict:
	safe_exec(
		self.condition, get_safe_globals(), dict(doc=self)
	)
	language_code = frappe.db.get_value(
		"WhatsApp Templates", self.template,
		fieldname='language_code'
	)
	if language_code:
		for contact in self._contact_list:
			data = {
				"messaging_product": "whatsapp",
				"to": self.format_number(contact),
				"type": "template",
				"template": {
					"name": self.template,
					"language": {
						"code": language_code
					},
					"components": []
				}
			}

			self.notify(data)
	# return _globals.frappe.flags

def send_template_message(self, doc: Document, contact_no = None):
	"""Specific to Document Event triggered Server Scripts."""
	if not self.enabled:
		return

	doc_data = doc.as_dict()
	if self.condition:
		# check if condition satisfies
		if not frappe.safe_eval(
			self.condition, get_safe_globals(), dict(doc=doc_data)
		):
			return

	template = frappe.db.get_value(
		"WhatsApp Templates", self.custom_whatsapp_template,
		fieldname='*'
	)


	if template:
		for row in self.recipients:
			if row.receiver_by_document_field != "owner":
				if not contact_no:
					contact_no = doc.get(row.receiver_by_document_field)
				if contact_no:
					data = {
						"messaging_product": "whatsapp",
						"to": contact_no,
						"type": "template",
						"template": {
							"name": self.custom_whatsapp_template,
							"language": {
								"code": template.language_code
							},
							"components": []
						}
					}

					# Pass parameter values
					if self.fields:
						parameters = []
						for field in self.fields:
							parameters.append({
								"type": "text",
								"text": doc.get_formatted(field.field_name)
							})

						data['template']["components"] = [{
							"type": "body",
							"parameters": parameters
						}]

					if self.attach_print:
						key = doc.get_document_share_key()
						frappe.db.commit()

						link = get_pdf_link(
							doc_data['doctype'],
							doc_data['name'],
							print_format=self.print_format or "Standard"
						)

						filename = f'{doc_data["name"]}.pdf'
						url = f'{frappe.utils.get_url()}{link}&key={key}'

						data['template']['components'].append({
							"type": "header",
							"parameters": [{
								"type": "document",
								"document": {
									"link": url,
									"filename": filename
								}
							}]
						})
						label = f"{doc_data['doctype']} - {doc_data['name']}"

					notify(self, data, label)

def notify(self, data, label = None):
	"""Notify."""
	settings = frappe.get_doc(
		"WhatsApp Settings", "WhatsApp Settings",
	)
	token = settings.get_password("token")

	headers = {
		"authorization": f"Bearer {token}",
		"content-type": "application/json"
	}
	try:
		response = make_post_request(
			f"{settings.url}/{settings.version}/{settings.phone_id}/messages",
			headers=headers, data=json.dumps(data)
		)

		message_id = response['messages'][0]['id']
		enqueue(save_whatsapp_log, data = data, message_id = message_id, label = label)

		frappe.msgprint("WhatsApp Message Triggered", indicator="green", alert=True)

	except Exception as e:
		response = frappe.flags.integration_request.json()['error']
		error_message = response.get('Error', response.get("message"))
		frappe.msgprint(
			f"Failed to trigger whatsapp message: {error_message}",
			indicator="red",
			alert=True
		)
	finally:
		status_response = frappe.flags.integration_request.json().get('error')
		frappe.get_doc({
			"doctype": "Integration Request",
			"integration_request_service": self.custom_whatsapp_template,
			"output": str(frappe.flags.integration_request.json()),
			"status": "Failed" if status_response else "Completed"
		}).insert(ignore_permissions=True)

def format_number(self, number):
	if (number.startswith("+")):
		number = number[1:len(number)]

	return number

@frappe.whitelist()
def send_notification(notification, ref_doctype, ref_docname, mobile_no = None):
	noti_doc = frappe.get_doc("Notification", notification)

	ref_doc = frappe.get_doc(ref_doctype, ref_docname)
	
	send_template_message(noti_doc, ref_doc, mobile_no)

def save_whatsapp_log(data, message_id, label = None):
	frappe.get_doc({
			"doctype": "WhatsApp Message",
			"type": "Outgoing",
			"message": str(data['template']),
			"to": data['to'],
			"message_type": "Template",
			"message_id": message_id,
			"content_type": "document",
			"label": label
		}).save(ignore_permissions=True)