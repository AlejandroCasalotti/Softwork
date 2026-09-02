import importlib


class OdooExternalConnectionGateway:
    """Read-only entry point from the original SCE stack to sce_connect."""

    def __init__(self, connection, env=None, session=None):
        self.connection = connection
        self.env = env or connection.env
        self._connection_service = self._build_connection_service(session=session)

    def _build_connection_service(self, session=None):
        try:
            module = importlib.import_module(
                "odoo.addons.sce_connect.services.connection_service"
            )
        except ImportError as error:
            raise RuntimeError(
                "SCE Connect debe estar instalado para usar conexiones Odoo JSON-2."
            ) from error
        return module.ConnectionService(self.connection, env=self.env, session=session)

    def test_connection(self):
        return self._connection_service.test_connection()

    def metadata(self, model):
        return self._connection_service.metadata(model)

    def read(self, model, ids, fields=None):
        return self._connection_service.read(model, ids, fields)

    def search(self, model, domain=None, offset=0, limit=None, order=None):
        return self._connection_service.search(
            model, domain=domain, offset=offset, limit=limit, order=order
        )

    def search_read(self, model, domain=None, fields=None, offset=0, limit=None, order=None):
        return self._connection_service.search_read(
            model,
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order,
        )
