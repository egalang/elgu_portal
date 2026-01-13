from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
import base64


class ElguMyRequests(http.Controller):

    @http.route(["/my/elgu/requests/<int:request_id>"], type="http", auth="user", website=True)
    def my_elgu_request_detail(self, request_id, **kw):
        rec = request.env["elgu.request"].browse(request_id)

        if not rec.exists():
            return request.not_found()

        # Odoo 19: unified access check (rights + rules)
        try:
            rec.check_access("read")
        except AccessError:
            return request.not_found()

        required_docs = rec.document_ids.filtered(lambda d: d.is_required)
        missing_required = required_docs.filtered(lambda d: not d.attachment_id)

        return request.render(
            "elgu_portal.portal_my_elgu_request_detail",
            {
                "req": rec,
                "missing_required_count": len(missing_required),
                "success": kw.get("success"),
                "error": kw.get("error"),
            },
        )

    @http.route(
        ["/my/elgu/requests/<int:request_id>/upload/<int:doc_id>"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def my_elgu_request_upload(self, request_id, doc_id, **post):
        req_rec = request.env["elgu.request"].browse(request_id)
        doc = request.env["elgu.request.document"].browse(doc_id)

        if not req_rec.exists() or not doc.exists() or doc.request_id.id != req_rec.id:
            return request.not_found()

        # Odoo 19: unified access check
        try:
            req_rec.check_access("write")
            doc.check_access("write")
        except AccessError:
            return request.not_found()

        uploaded = request.httprequest.files.get("file")
        if not uploaded or not getattr(uploaded, "filename", ""):
            return request.redirect(f"/my/elgu/requests/{request_id}?error=Please+select+a+file")

        file_bytes = uploaded.read()
        if not file_bytes:
            return request.redirect(f"/my/elgu/requests/{request_id}?error=Uploaded+file+is+empty")

        attachment = request.env["ir.attachment"].sudo().create({
            "name": uploaded.filename,
            "datas": base64.b64encode(file_bytes),
            "res_model": "elgu.request",
            "res_id": req_rec.id,
            "mimetype": getattr(uploaded, "content_type", None),
        })

        doc.sudo().write({
            "attachment_id": attachment.id,
            "status": "submitted",
        })

        return request.redirect(f"/my/elgu/requests/{request_id}?success=File+uploaded")

    @http.route(["/my/elgu/requests/<int:request_id>/pay"], type="http", auth="user", website=True)
    def my_elgu_request_pay(self, request_id, **kw):
        req_rec = request.env["elgu.request"].browse(request_id)
        if not req_rec.exists():
            return request.not_found()

        try:
            req_rec.check_access("read")
        except AccessError:
            return request.not_found()

        if (req_rec.amount_total or 0.0) <= 0.0:
            return request.redirect(f"/my/elgu/requests/{request_id}?error=No+payment+required")

        if not req_rec.invoice_id:
            try:
                req_rec.sudo().action_create_invoice()
            except Exception:
                return request.redirect(f"/my/elgu/requests/{request_id}?error=Failed+to+create+invoice")

        if req_rec.invoice_id:
            invoice = req_rec.invoice_id.sudo()
            invoice._portal_ensure_token()
            return request.redirect(f"/my/invoices/{invoice.id}?access_token={invoice.access_token}")

        return request.redirect(f"/my/elgu/requests/{request_id}?error=Invoice+not+created")
    
    @http.route(["/my/elgu/requests/<int:request_id>/download"], type="http", auth="user", website=True)
    def my_elgu_request_download(self, request_id, **kw):
        req_rec = request.env["elgu.request"].browse(request_id)
        if not req_rec.exists():
            return request.not_found()

        # Ownership check (Odoo 19 style)
        try:
            req_rec.check_access("read")
        except AccessError:
            return request.not_found()

        # Gate 1: must be paid (if invoiced)
        if req_rec.invoice_id and req_rec.invoice_id.payment_state != "paid":
            return request.redirect(f"/my/elgu/requests/{request_id}?error=Payment+required")

        # Gate 2: required docs must be accepted (or at least uploaded — you choose)
        # Here we enforce ACCEPTED for required docs:
        required_docs = req_rec.document_ids.filtered(lambda d: d.is_required)
        not_accepted = required_docs.filtered(lambda d: (d.status or "missing") != "accepted")
        if not_accepted:
            return request.redirect(f"/my/elgu/requests/{request_id}?error=Requirements+not+yet+accepted")

        # Gate 3: must have released document
        attachment = req_rec.released_attachment_id
        if not attachment:
            return request.redirect(f"/my/elgu/requests/{request_id}?error=Released+document+not+available")

        # Extra guard: ensure attachment is actually linked to this request
        # (recommended; prevents staff accidentally linking wrong file)
        if attachment.res_model and attachment.res_id:
            if attachment.res_model != "elgu.request" or attachment.res_id != req_rec.id:
                return request.redirect(f"/my/elgu/requests/{request_id}?error=Invalid+released+document+link")

        # Use Odoo’s own /web/content handler (it enforces attachment access rules)
        return request.redirect(f"/web/content/{attachment.id}?download=true")

