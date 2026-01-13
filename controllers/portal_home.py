from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class ElguCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if "elgu_request_count" in counters:
            partner = request.env.user.partner_id
            values["elgu_request_count"] = request.env["elgu.request"].search_count([
                ("applicant_id", "=", partner.id)
            ])

        return values
