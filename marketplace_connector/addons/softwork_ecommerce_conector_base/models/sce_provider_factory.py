# -*- coding: utf-8 -*-
from odoo import models

from ..services.provider_factory import ProviderFactory


class SceProviderFactory(models.AbstractModel):
    _name = "sce.provider.factory"
    _description = "SCE Provider Factory"

    def get_provider(self, account):
        return ProviderFactory.get_provider(account)