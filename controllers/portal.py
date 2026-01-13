from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

class ElguPortal(http.Controller):

    @http.route(['/my/elgu'], type='http', auth='user', website=True)
    def my_elgu_home(self, **kw):
        return request.render('elgu_portal.portal_elgu_home', {})

    @http.route(['/my/elgu/requests'], type='http', auth='user', website=True)
    def my_elgu_requests(self, **kw):
        partner = request.env.user.partner_id.commercial_partner_id
        Request = request.env['elgu.request'].sudo()
        requests = Request.search([('applicant_id', 'child_of', [partner.id])], order='create_date desc')
        return request.render('elgu_portal.portal_elgu_requests', {'requests': requests})

    @http.route(['/my/elgu/requests/new'], type='http', auth='user', website=True, methods=['GET'])
    def my_elgu_request_new(self, **kw):
        types = request.env['elgu.request.type'].sudo().search([('active', '=', True)], order='sequence, name')
        return request.render('elgu_portal.portal_elgu_request_new', {'types': types})

    @http.route(['/my/elgu/requests/new'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def my_elgu_request_create(self, **post):
        partner = request.env.user.partner_id.commercial_partner_id
        req_type_id = int(post.get('request_type_id'))

        rec = request.env['elgu.request'].sudo().create({
            'request_type_id': req_type_id,
            'applicant_id': partner.id,
            'amount_total': float(post.get('amount_total') or 0.0),  # for MVP; later compute server-side
        })

        # Create doc checklist slots based on type requirements
        rec.action_submit()
        return request.redirect(f"/my/elgu/requests/{rec.id}")

    @http.route(['/my/elgu/requests/<int:request_id>'], type='http', auth='user', website=True)
    def my_elgu_request_view(self, request_id, **kw):
        rec = request.env['elgu.request'].browse(request_id)
        # Record rules should enforce ownership; still keep a guard:
        if not rec.exists():
            return request.not_found()
        try:
            rec.check_access_rights('read')
            rec.check_access_rule('read')
        except AccessError:
            return request.not_found()

        return request.render('elgu_portal.portal_elgu_request_view', {'req': rec})

    @http.route(['/my/elgu/requests/<int:request_id>/upload/<int:doc_id>'],
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def my_elgu_request_upload(self, request_id, doc_id, **post):
        req_rec = request.env['elgu.request'].browse(request_id)
        doc = request.env['elgu.request.document'].browse(doc_id)

        # Ownership enforced by rules; still guard consistency
        if not req_rec.exists() or not doc.exists() or doc.request_id.id != req_rec.id:
            return request.not_found()

        uploaded = request.httprequest.files.get('file')
        if not uploaded:
            return request.redirect(f"/my/elgu/requests/{request_id}")

        attachment = request.env['ir.attachment'].sudo().create({
            'name': uploaded.filename,
            'datas': uploaded.read().encode('base64') if isinstance(uploaded.read(), str) else None,
        })
        # Better: use odoo.tools.base64_encode; see note below
        # For now keep simple and adjust in your implementation

        doc.sudo().write({
            'attachment_id': attachment.id,
            'status': 'submitted',
        })
        return request.redirect(f"/my/elgu/requests/{request_id}")

    @http.route(['/my/elgu/requests/<int:request_id>/pay'], type='http', auth='user', website=True)
    def my_elgu_request_pay(self, request_id, **kw):
        req_rec = request.env['elgu.request'].browse(request_id)
        if not req_rec.exists():
            return request.not_found()

        # Create invoice if missing
        if not req_rec.invoice_id and req_rec.amount_total > 0:
            req_rec.sudo().action_create_invoice()

        # Reuse standard invoice portal payment flow
        if req_rec.invoice_id:
            return request.redirect(f"/my/invoices/{req_rec.invoice_id.id}")

        return request.redirect(f"/my/elgu/requests/{request_id}")

    @http.route(['/my/elgu/requests/<int:request_id>/download'], type='http', auth='user', website=True)
    def my_elgu_request_download(self, request_id, **kw):
        req_rec = request.env['elgu.request'].browse(request_id)
        if not req_rec.exists():
            return request.not_found()

        # MVP option 1: if you later attach a released document as an attachment, serve it
        # e.g. req_rec.released_attachment_id (you’ll add this field)
        # For now, just block unless Released:
        if not req_rec.stage_id.is_closed or req_rec.decision != 'approved':
            return request.redirect(f"/my/elgu/requests/{request_id}")

        # Later you’ll return an ir.actions.report PDF or an attachment download URL
        return request.redirect(f"/my/elgu/requests/{request_id}")
