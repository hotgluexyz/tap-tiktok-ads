"""REST client handling, including TikTokStream base class."""

from __future__ import annotations

import json
from typing import Any, cast

import requests
from hotglue_etl_exceptions import InvalidCredentialsError
from hotglue_singer_sdk.exceptions import FatalAPIError
from hotglue_singer_sdk.helpers.jsonpath import extract_jsonpath
from hotglue_singer_sdk.streams import RESTStream

DATE_FORMAT = "%Y-%m-%d"
TIKTOK_API_BASE = "https://business-api.tiktok.com/open_api/v1.3"
INVALID_CREDENTIAL_CODES = {40002, 40100, 40101, 40102, 40103, 40104, 40105}


class TikTokStream(RESTStream):
    url_base = TIKTOK_API_BASE
    records_jsonpath = "$.data.list[*]"

    def primary_advertiser_id(self) -> str:
        return cast(Any, self._tap).advertiser_id_list[0]

    @property
    def http_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if user_agent := self.config.get("user_agent"):
            headers["User-Agent"] = str(user_agent)
        headers["Access-Token"] = str(self.config["access_token"])
        return headers

    def validate_response(self, response: requests.Response) -> None:
        super().validate_response(response)
        payload = response.json()
        code = payload.get("code")
        if code in (0, None):
            return
        message = payload.get("message") or response.text
        if code in INVALID_CREDENTIAL_CODES:
            raise InvalidCredentialsError(f"TikTok API auth error ({code}): {message}")
        raise FatalAPIError(f"TikTok API error ({code}): {message}")

    @staticmethod
    def _get_page_info(json_path: str, json_payload: dict[str, Any]) -> Any:
        page_matches = extract_jsonpath(json_path, json_payload)
        return next(iter(page_matches), None)

    def get_next_page_token(
        self, response: requests.Response, previous_token: Any | None
    ) -> Any | None:
        current_page = self._get_page_info("$.data.page_info.page", response.json()) or 0
        total_pages = self._get_page_info("$.data.page_info.total_page", response.json()) or 0
        if current_page < total_pages:
            return current_page + 1
        return None

    def get_url_params(
        self, context: dict | None, next_page_token: Any | None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"advertiser_id": self.primary_advertiser_id()}
        if next_page_token:
            params["page"] = next_page_token
        params["filtering"] = json.dumps(
            {
                "primary_status": "STATUS_ALL"
                if self.config.get("include_deleted")
                else "STATUS_NOT_DELETE"
            }
        )
        params["page_size"] = 10
        return params


class TikTokReportsStream(TikTokStream):
    url_base = f"{TIKTOK_API_BASE}/report/integrated/get/"
    records_jsonpath = "$.data.list[*]"
    next_page_token_jsonpath = "$.page_info.page"

    def post_process(self, row: dict, context: dict | None = None) -> dict | None:
        return {**row["dimensions"], **row["metrics"]}

    def get_next_page_token(
        self, response: requests.Response, previous_token: Any | None
    ) -> Any | None:
        page_match = self._get_page_info("$.data.page_info.page", response.json()) or 0
        total_pages_match = self._get_page_info("$.data.page_info.total_page", response.json()) or 0
        if page_match < total_pages_match:
            return page_match + 1
        return None
