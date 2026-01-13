from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from odoo.tools import html_escape

class ElguBusinessPermitPortal(http.Controller):

    @http.route("/services/business-permit", type="http", auth="public", website=True, sitemap=True)
    def business_permit_page(self, **kw):
        RequestType = request.env["elgu.request.type"].sudo()
        types = RequestType.search(
            [("code", "in", ["BP_NEW", "BP_RENEW"]), ("active", "=", True)],
            order="sequence, name",
        )
        types_by_code = {t.code: t for t in types}
        return request.render(
            "elgu_portal.portal_service_business_permit",
            {
                "bp_new": types_by_code.get("BP_NEW"),
                "bp_renew": types_by_code.get("BP_RENEW"),
                "is_public_user": request.env.user._is_public(),
            },
        )

    # -------- PAGE 3: APPLY (GET) --------
    @http.route(
        ["/services/business-permit/apply/<string:code>"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
        sitemap=False,
    )
    def business_permit_apply_get(self, code, **kw):
        code = (code or "").strip().upper()
        if code not in ("BP_NEW", "BP_RENEW"):
            return request.not_found()

        req_type = request.env["elgu.request.type"].sudo().search(
            [("code", "=", code), ("active", "=", True)],
            limit=1,
        )
        if not req_type:
            return request.not_found()

        partner = request.env.user.partner_id.commercial_partner_id

        return request.render(
            "elgu_portal.portal_business_permit_apply",
            {
                "req_type": req_type,
                "code": code,
                "partner": partner,
                "error": kw.get("error"),
            },
        )

    # -------- PAGE 3: APPLY (POST) --------
    @http.route(
        ["/services/business-permit/apply/<string:code>"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
        sitemap=False,
    )
    def business_permit_apply_post(self, code, **post):
        code = (code or "").strip().upper()
        if code not in ("BP_NEW", "BP_RENEW"):
            return request.not_found()

        req_type = request.env["elgu.request.type"].sudo().search(
            [("code", "=", code), ("active", "=", True)],
            limit=1,
        )
        if not req_type:
            return request.not_found()

        partner = request.env.user.partner_id.commercial_partner_id

        # Minimal fields for MVP (add more later)
        business_name = (post.get("business_name") or "").strip()
        trade_name = (post.get("trade_name") or "").strip()
        business_address = (post.get("business_address") or "").strip()
        notes = (post.get("notes") or "").strip()

        if not business_name:
            # re-render same form with error
            return request.render(
                "elgu_portal.portal_business_permit_apply",
                {
                    "req_type": req_type,
                    "code": code,
                    "partner": partner,
                    "error": "Business Name is required.",
                },
            )

        # Create request (sudo is ok; record rules will be handled on Page 4)
        Request = request.env["elgu.request"].sudo()

        vals = {
            "request_type_id": req_type.id,
            "applicant_id": partner.id,
            # store these temporarily in notes fields for now
            # (later we’ll add proper business fields on elgu.request)
            "department_notes": f"Business Name: {business_name}\nTrade Name: {trade_name}\nAddress: {business_address}".strip(),
            "decision_notes": notes,
            "amount_total": req_type.fee_amount or 0.0
        }

        rec = Request.create(vals)

        # Create document checklist lines from requirement_ids
        Doc = request.env["elgu.request.document"].sudo()
        for req in req_type.requirement_ids.sorted(lambda r: r.sequence):
            Doc.create({
                "request_id": rec.id,
                "requirement_id": req.id,
                "is_required": bool(req.required),
                "status": "missing",
            })

        # Optional: move to Submitted stage if your workflow supports it
        # Only do this if you have a seed stage with XML id stage_submitted
        try:
            submitted_stage = request.env.ref("elgu_core.stage_submitted", raise_if_not_found=False)
            if submitted_stage:
                rec.stage_id = submitted_stage.id
        except Exception:
            pass

        # Redirect to Page 4 (we’ll build next)
        return request.redirect(f"/my/elgu/requests/{rec.id}")
