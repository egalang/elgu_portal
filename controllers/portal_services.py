from odoo import http
from odoo.http import request

class ElguPortalServices(http.Controller):

    @http.route(['/services'], type='http', auth='public', website=True)
    def elgu_services_home(self, **kw):
        # For now we hardcode categories/cards. Later we can drive these from elgu.request.type.
        services = [
            {
                "title": "Permits and Licenses",
                "items": [
                    {"label": "Business Permit", "href": "/services/business-permit"},
                    {"label": "Building Permit", "href": "/services/building-permit"},
                ],
            },
            {
                "title": "Taxation",
                "items": [
                    {"label": "Real Property Tax (RPT)", "href": "/services/rpt"},
                    {"label": "Community Tax Certificate (Cedula)", "href": "/services/cedula"},
                ],
            },
            {
                "title": "Civil Registry",
                "items": [
                    {"label": "Birth Certificate", "href": "/services/birth-certificate"},
                    {"label": "Death Certificate", "href": "/services/death-certificate"},
                    {"label": "Marriage Certificate", "href": "/services/marriage-certificate"},
                ],
            },
        ]
        return request.render("elgu_portal.portal_services_home", {"services": services})
