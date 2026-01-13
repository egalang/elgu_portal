from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class ElguCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'elgu_request_count' in counters:
            partner = request.env.user.partner_id
            values['elgu_request_count'] = request.env['elgu.request'].search_count([
                ('applicant_id', '=', partner.id)
            ])
        return values

    @http.route(['/my/elgu/requests', '/my/elgu/requests/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_elgu_requests(self, page=1, sortby='date', **kw):
        partner = request.env.user.partner_id
        domain = [('applicant_id', '=', partner.id)]

        searchbar_sortings = {
            "date": {"label": "Newest", "order": "create_date desc, id desc"},
            "name": {"label": "Request No.", "order": "name desc"},
            "stage": {"label": "Stage", "order": "stage_id asc, id desc"},
        }
        order = searchbar_sortings.get(sortby, searchbar_sortings["date"])["order"]

        step = 20
        total = request.env['elgu.request'].search_count(domain)
        pager = portal_pager(url="/my/elgu/requests", total=total, page=page, step=step, url_args={'sortby': sortby})

        requests_recs = request.env['elgu.request'].search(domain, order=order, limit=step, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            "page_name": "elgu_requests",
            "requests": requests_recs,
            "pager": pager,
            "sortby": sortby,
            "searchbar_sortings": searchbar_sortings,
        })
        return request.render("elgu_portal.portal_my_elgu_requests", values)
