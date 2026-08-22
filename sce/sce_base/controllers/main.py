# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Main Controllers
"""

from odoo import http
from odoo.http import request


class SCEMainController(http.Controller):
    """
    Main HTTP endpoints for the Softwork Commerce Engine.

    These endpoints are intended for health checks,
    diagnostics and framework information.
    """

    # -------------------------------------------------------------------------
    # Framework Information
    # -------------------------------------------------------------------------

    @http.route(
        "/sce",
        type="jsonrpc",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def index(self):
        """
        Returns basic framework information.
        """

        return {
            "application": "Softwork Commerce Engine",
            "framework": "SCE",
            "status": "running",
            "version": "19.0.1.0.0",
        }

    # -------------------------------------------------------------------------
    # Ping
    # -------------------------------------------------------------------------

    @http.route(
        "/sce/ping",
        type="jsonrpc",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def ping(self):
        """
        Simple heartbeat endpoint.
        """

        return {
            "pong": True,
        }

    # -------------------------------------------------------------------------
    # Framework Details
    # -------------------------------------------------------------------------

    @http.route(
        "/sce/info",
        type="jsonrpc",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def info(self):
        """
        Returns framework information.
        """

        return {
            "application": "Softwork Commerce Engine",
            "framework": "SCE",
            "module": "sce_base",
            "version": "19.0.1.0.0",
            "company": request.env.company.name,
            "database": request.env.cr.dbname,
        }

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------

    @http.route(
        "/sce/health",
        type="jsonrpc",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def health(self):
        """
        Returns current framework health.
        """

        return {
            "status": "healthy",
            "framework": "SCE",
            "version": "19.0.1.0.0",
            "database": request.env.cr.dbname,
            "company": request.env.company.name,
            "user": request.env.user.name,
        }