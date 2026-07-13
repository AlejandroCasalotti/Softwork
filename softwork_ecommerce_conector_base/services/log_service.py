# -*- coding: utf-8 -*-
import json

from odoo import models


class SceLogService(models.AbstractModel):
    _name = "sce.log.service"
    _description = "SCE Log Service"

    def log(
        self,
        *,
        name,
        message,
        level="INFO",
        connector=None,
        account=None,
        job=None,
        details_json=None,
        provider=None,
        operation=None,
        elapsed_ms=None,
    ):
        details = {}
        if details_json:
            try:
                details = json.loads(details_json) if isinstance(details_json, str) else dict(details_json)
            except Exception:
                details = {"raw_details": str(details_json)}

        details.setdefault("provider", provider or (connector.provider_type if connector else False))
        details.setdefault("operation", operation or False)
        details.setdefault("elapsed_ms", elapsed_ms if elapsed_ms is not None else False)
        details.setdefault("account_id", account.id if account else False)

        vals = {
            "name": name,
            "message": message,
            "level": level,
            "connector_id": connector.id if connector else False,
            "account_id": account.id if account else False,
            "job_id": job.id if job else False,
            "details_json": json.dumps(details),
            "company_id": (account.company_id.id if account else self.env.company.id),
        }
        return self.env["sce.log"].sudo().create(vals)