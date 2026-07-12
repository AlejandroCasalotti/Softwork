# -*- coding: utf-8 -*-
from odoo import models


class SceLogService(models.AbstractModel):
    _name = "sce.log.service"
    _description = "SCE Log Service"

    def log(self, *, name, message, level="INFO", connector=None, account=None, job=None, details_json=None):
        vals = {
            "name": name,
            "message": message,
            "level": level,
            "connector_id": connector.id if connector else False,
            "account_id": account.id if account else False,
            "job_id": job.id if job else False,
            "details_json": details_json or False,
            "company_id": (account.company_id.id if account else self.env.company.id),
        }
        return self.env["sce.log"].sudo().create(vals)