# -*- coding: utf-8 -*-

from __future__ import annotations

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    """
    HTTP client wrapper for SCE.

    Provides a shared requests.Session with sensible defaults,
    retry strategy and helper methods.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        timeout: int | None = None,
        retries: int = 3,
        backoff: float = 0.5,
    ):
        self.timeout = timeout or self.DEFAULT_TIMEOUT

        self.session = requests.Session()

        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            allowed_methods={
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
            },
            status_forcelist={
                429,
                500,
                502,
                503,
                504,
            },
            backoff_factor=backoff,
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry)

        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # ---------------------------------------------------------

    def request(self, method: str, url: str, **kwargs) -> Response:

        kwargs.setdefault("timeout", self.timeout)

        return self.session.request(method, url, **kwargs)

    # ---------------------------------------------------------

    def get(self, url, **kwargs):

        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):

        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):

        return self.request("PUT", url, **kwargs)

    def patch(self, url, **kwargs):

        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):

        return self.request("DELETE", url, **kwargs)

    def close(self):

        self.session.close()