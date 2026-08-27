import unittest
from unittest.mock import Mock

import requests

from ..services.errors import ApiError, AuthenticationError, NetworkError, PermissionError
from ..services.mercadolibre_transport import MercadoLibreConnectTransport


class FakeResponse:
    is_redirect = False
    is_permanent_redirect = False

    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}

    def json(self):
        return self.payload


class MercadoLibreTransportTests(unittest.TestCase):
    def test_allowed_token_and_user_endpoints(self):
        session = Mock()
        session.request.return_value = FakeResponse(payload={"id": 123})
        transport = MercadoLibreConnectTransport(session=session)
        self.assertEqual(
            transport.request("GET", "https://api.mercadolibre.com/users/me", access_token="token"),
            {"id": 123},
        )
        self.assertEqual(session.request.call_args.kwargs["headers"]["Authorization"], "Bearer token")

    def test_arbitrary_endpoint_is_blocked(self):
        transport = MercadoLibreConnectTransport(session=Mock())
        with self.assertRaises(ApiError):
            transport.request("GET", "https://example.com/users/me")

    def test_error_mapping(self):
        for status, error_type in ((401, AuthenticationError), (403, PermissionError), (500, ApiError)):
            session = Mock()
            session.request.return_value = FakeResponse(status_code=status)
            with self.subTest(status=status), self.assertRaises(error_type):
                MercadoLibreConnectTransport(session=session).request(
                    "GET", "https://api.mercadolibre.com/users/me", access_token="token"
                )

    def test_timeout_mapping(self):
        session = Mock()
        session.request.side_effect = requests.Timeout()
        with self.assertRaises(NetworkError):
            MercadoLibreConnectTransport(session=session).request(
                "GET", "https://api.mercadolibre.com/users/me", access_token="token"
            )


if __name__ == "__main__":
    unittest.main()
