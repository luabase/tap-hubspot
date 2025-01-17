"""REST client handling, including HubspotStream base class."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Iterable

import requests
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.pagination import BaseAPIPaginator
from singer_sdk.streams import RESTStream

if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    from cached_property import cached_property

from singer_sdk.authenticators import (
    BearerTokenAuthenticator,
)

_Auth = Callable[[requests.PreparedRequest], requests.PreparedRequest]


class HubspotStream(RESTStream):
    """tap-hubspot stream class."""

    @property
    def url_base(self) -> str:
        """
        Returns base url
        """
        base_url = "https://api.hubapi.com/"
        return base_url

    records_jsonpath = "$[*]"  # Or override `parse_response`.

    # Set this value or override `get_new_paginator`.
    next_page_token_jsonpath = "$.next_page"

    @cached_property
    def authenticator(self) -> _Auth:
        """Return a new authenticator object.

        Returns:
            An authenticator instance.
        """

        access_token = self.config.get("access_token")

        return BearerTokenAuthenticator.create_for_stream(
            self,
            token=access_token,
        )

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed.

        Returns:
            A dictionary of HTTP headers.
        """
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        return headers

    def get_new_paginator(self) -> BaseAPIPaginator:
        """Create a new pagination helper instance.

        If the source API can make use of the `next_page_token_jsonpath`
        attribute, or it contains a `X-Next-Page` header in the response
        then you can remove this method.

        If you need custom pagination that uses page numbers, "next" links, or
        other approaches, please read the guide: https://sdk.meltano.com/en/v0.25.0/guides/pagination-classes.html.

        Returns:
            A pagination helper instance.
        """
        return super().get_new_paginator()

    def get_next_page_token(
        self,
        response: requests.Response,
        previous_token: t.Any | None,
    ) -> t.Any | None:
        """Return a token for identifying next page or None if no more pages."""
        # If pagination is required, return a token which can be used to get the
        #       next page. If this is the final page, return "None" to end the
        #       pagination loop.
        resp_json = response.json()
        paging = resp_json.get("paging")

        if paging is not None:
            next_page_token = resp_json.get("paging", {}).get("next", {}).get("after")
        else:
            next_page_token = None
        return next_page_token

    def get_url_params(
        self,
        context: dict | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization.

        Args:
            context: The stream context.
            next_page_token: The next page index or value.

        Returns:
            A dictionary of URL query parameters.
        """
        params: dict = {}
        if next_page_token:
            params["after"] = next_page_token
        if self.replication_key:
            params["sort"] = "asc"
            params["order_by"] = self.replication_key
        if hasattr(self, "property_list"):
            params["properties"] = self.property_list.to_dict()["properties"].keys()

        return params
