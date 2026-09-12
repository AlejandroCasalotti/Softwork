# -*- coding: utf-8 -*-

from . import models


def post_init_migrate_legacy_marketplace(env):
	products = env["product.template"].search(
		[
			"|",
			"|",
			"|",
			("ml_item_id", "!=", False),
			("ml_category_id", "!=", False),
			("ml_title", "!=", False),
			("ml_attributes_json", "!=", False),
			("ml_pictures_json", "!=", False),
		]
	)
	for product in products:
		product._migrate_legacy_marketplace_data()