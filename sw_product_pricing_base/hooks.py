# -*- coding: utf-8 -*-

"""
Softwork Product Pricing Base

Lifecycle hooks for module installation, upgrade and removal.

These hooks are intentionally lightweight. Future versions may use
them to create default data, migrate existing records, recalculate
pricing information or perform cleanup tasks.
"""

from __future__ import annotations

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Executed immediately after the module is installed.

    Reserved for:
        - Creating default configuration
        - Creating default pricing rules
        - Initializing company settings
        - Data migrations
    """
    if not isinstance(env, api.Environment):
        env = api.Environment(env, SUPERUSER_ID, {})

    _logger.info(
        "Softwork Product Pricing Base: post_init_hook executed."
    )


def uninstall_hook(env):
    """
    Executed immediately before the module is uninstalled.

    Reserved for:
        - Cleaning temporary data
        - Removing generated records
        - Logging uninstall information
    """
    if not isinstance(env, api.Environment):
        env = api.Environment(env, SUPERUSER_ID, {})

    _logger.info(
        "Softwork Product Pricing Base: uninstall_hook executed."
    )