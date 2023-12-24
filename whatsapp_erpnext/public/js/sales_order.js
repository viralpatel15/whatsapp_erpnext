frappe.ui.form.on('Sales Order', {
    onload: function(frm){
        let fields = [
			{
				label: __("Select Notification"),
				fieldtype:'Link',
				fieldname: 'notification',
                options: "Notification",
                filters: {
                    "channel": "WhatsApp",
                    "document_type": frm.doc.doctype
                },
                reqd: 1
			},
            {
				label: __("Mobile No"),
				fieldtype:'Data',
				fieldname: 'mobile_no',
				options: "Phone",
				default: frm.doc.contact_mobile,
				reqd: 1
			}
		];
        frm.page.add_menu_item(
            __("Send WhatsApp Message"),
            () => {
                frm.dialog = new frappe.ui.Dialog({
                    title: __("Send WhatsApp Message"),
                    fields: fields
                });
                frm.dialog.set_primary_action(__("Send Message"), function(){
                    frm.values = frm.dialog.get_values();
                    frappe.call({ 
                        method: 'whatsapp_erpnext.whatsapp_erpnext.doc_events.notification.send_notification',
                        args: {
                            "notification": frm.values.notification,
                            "ref_doctype" : frm.doc.doctype,
                            "ref_docname": frm.doc.name,
                            "mobile_no": frm.values.mobile_no
                        },
                        callback: (r) => {
                            frm.dialog.hide();
                        }})
                })
                frm.dialog.show();
            },
            true
        );
    }
})