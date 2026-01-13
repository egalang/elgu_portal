# from odoo import http


# class ElguPortal(http.Controller):
#     @http.route('/elgu_portal/elgu_portal', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/elgu_portal/elgu_portal/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('elgu_portal.listing', {
#             'root': '/elgu_portal/elgu_portal',
#             'objects': http.request.env['elgu_portal.elgu_portal'].search([]),
#         })

#     @http.route('/elgu_portal/elgu_portal/objects/<model("elgu_portal.elgu_portal"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('elgu_portal.object', {
#             'object': obj
#         })

