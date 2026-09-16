"""GMV Max streams for tap-tiktok-ads."""

from __future__ import annotations

import copy
import datetime
import json
from collections.abc import Iterable
from typing import Any
from urllib.parse import parse_qs, urlparse

import dateutil
import requests
from hotglue_singer_sdk import typing as th

from tap_tiktok_ads.client import TikTokGmvMaxReportStream, TikTokStream
from tap_tiktok_ads.streams import DATE_FORMAT, STEP_NUM_DAYS

GMV_MAX_CAMPAIGN_PROMOTION_TYPES = ["PRODUCT_GMV_MAX", "LIVE_GMV_MAX"]

PRODUCT_CAMPAIGN_REPORT_METRICS = [
    "campaign_id",
    "operation_status",
    "campaign_name",
    "schedule_type",
    "schedule_start_time",
    "schedule_end_time",
    "target_roi_budget",
    "bid_type",
    "max_delivery_budget",
    "roas_bid",
    "cost",
    "net_cost",
    "orders",
    "cost_per_order",
    "gross_revenue",
    "roi",
]

LIVE_CAMPAIGN_REPORT_METRICS = [
    "campaign_id",
    "operation_status",
    "campaign_name",
    "tt_account_name",
    "tt_account_profile_image_url",
    "identity_id",
    "bid_type",
    "schedule_type",
    "schedule_start_time",
    "schedule_end_time",
    "target_roi_budget",
    "max_delivery_budget",
    "roas_bid",
    "cost",
    "net_cost",
    "orders",
    "cost_per_order",
    "gross_revenue",
    "roi",
    "live_views",
    "cost_per_live_view",
    "10_second_live_views",
    "cost_per_10_second_live_view",
    "live_follows",
]

REPORT_DIMENSIONS = ["campaign_id", "stat_time_day"]


class GmvMaxStoresStream(TikTokStream):
    """TikTok Shops available for GMV Max."""

    name = "gmv_max_stores"
    path = "/gmv_max/store/list/"
    primary_keys = ["store_id"]
    records_jsonpath = "$.data.store_list[*]"
    replication_key = None
    schema = th.PropertiesList(
        th.Property("store_id", th.StringType),
        th.Property("store_name", th.StringType),
        th.Property("store_code", th.StringType),
        th.Property("is_gmv_max_available", th.BooleanType),
        th.Property("is_owner_bc", th.BooleanType),
        th.Property("store_authorized_bc_id", th.StringType),
        th.Property("store_status", th.StringType),
        th.Property("store_role", th.StringType),
        th.Property("targeting_region_codes", th.ArrayType(th.StringType)),
        th.Property("thumbnail_url", th.StringType),
        th.Property("advertiser_id", th.StringType),
    ).to_dict()

    def get_url_params(
        self, context: dict | None, next_page_token: Any | None
    ) -> dict[str, Any]:
        """Request GMV Max shops for the configured advertiser."""
        return {"advertiser_id": self.primary_advertiser_id()}

    def get_next_page_token(
        self, response: requests.Response, previous_token: Any | None
    ) -> Any | None:
        """Store list is returned in a single response (no pagination)."""
        return None

    def post_process(self, row: dict, context: dict | None = None) -> dict | None:
        """Attach advertiser_id to each shop record."""
        record = dict(row)
        record["advertiser_id"] = self.primary_advertiser_id()
        return record

    def get_child_context(self, record: dict, context: dict | None) -> dict:
        """Pass shop context to GMV Max report child streams."""
        return {
            "store_id": str(record["store_id"]),
            "is_gmv_max_available": record.get("is_gmv_max_available", False),
        }


class GmvMaxCampaignsStream(TikTokStream):
    """GMV Max campaigns (Product and LIVE) for the advertiser."""

    name = "gmv_max_campaigns"
    path = "/gmv_max/campaign/get/"
    primary_keys = ["campaign_id"]
    records_jsonpath = "$.data.list[*]"
    replication_key = None
    schema = th.PropertiesList(
        th.Property("campaign_id", th.StringType),
        th.Property("campaign_name", th.StringType),
        th.Property("operation_status", th.StringType),
        th.Property("secondary_status", th.StringType),
        th.Property("store_id", th.StringType),
        th.Property("shopping_ads_type", th.StringType),
        th.Property("gmv_max_promotion_type", th.StringType),
        th.Property("schedule_type", th.StringType),
        th.Property("schedule_start_time", th.StringType),
        th.Property("schedule_end_time", th.StringType),
        th.Property("create_time", th.StringType),
        th.Property("modify_time", th.StringType),
        th.Property("advertiser_id", th.StringType),
    ).to_dict()

    def get_url_params(
        self, context: dict | None, next_page_token: Any | None
    ) -> dict[str, Any]:
        """List Product and LIVE GMV Max campaigns for the advertiser."""
        params: dict[str, Any] = {
            "advertiser_id": self.primary_advertiser_id(),
            "page_size": 50,
            "filtering": json.dumps(
                {"gmv_max_promotion_types": GMV_MAX_CAMPAIGN_PROMOTION_TYPES}
            ),
        }
        if next_page_token:
            params["page"] = next_page_token
        return params

    def post_process(self, row: dict, context: dict | None = None) -> dict | None:
        """Normalize promotion type and attach advertiser_id."""
        record = dict(row)
        record["advertiser_id"] = self.primary_advertiser_id()
        promo = (
            record.get("gmv_max_promotion_type")
            or record.get("shopping_ads_type")
            or record.get("promotion_type")
        )
        if promo:
            record["gmv_max_promotion_type"] = str(promo)
        return record


class GmvMaxCampaignMetricsByDayStream(TikTokGmvMaxReportStream):
    """Daily GMV Max campaign report for a single TikTok Shop."""

    report_promotion_types: list[str] = []
    tiktok_metrics: list[str] = []
    path = "/"
    replication_key = "stat_time_day"
    state_partitioning_keys = ["store_id"]

    def _store_reports_enabled(self, context: dict | None) -> bool:
        """Return whether the parent shop supports GMV Max reporting."""
        if context is None:
            return False
        return bool(context.get("is_gmv_max_available"))

    def get_records(self, context: dict | None) -> Iterable[dict]:
        """Skip sync when the shop is not GMV Max eligible."""
        if not self._store_reports_enabled(context):
            return
        yield from super().get_records(context)

    def get_url_params(
        self, context: dict | None, next_page_token: Any | None
    ) -> dict[str, Any]:
        """Build GMV Max report query params for one shop and date window."""
        if context is None or context.get("store_id") is None:
            raise RuntimeError(f"{self.name} requires parent store context with store_id")
        if isinstance(next_page_token, dict) and next_page_token.get("start_date") is not None:
            start_date = datetime.datetime.strptime(
                next_page_token["start_date"], DATE_FORMAT
            ).replace(tzinfo=datetime.timezone.utc)
        else:
            start_date = self.get_starting_timestamp(context)
            if start_date is None:
                start_date = dateutil.parser.isoparse(self.config["start_date"])
            lookback_window = self.config.get("lookback", 14)
            if lookback_window > 0:
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=datetime.timezone.utc)
                config_start_date = dateutil.parser.isoparse(self.config["start_date"])
                if config_start_date.tzinfo is None:
                    config_start_date = config_start_date.replace(
                        tzinfo=datetime.timezone.utc
                    )
                start_date = max(
                    min(
                        start_date,
                        datetime.datetime.now(tz=start_date.tzinfo)
                        - datetime.timedelta(days=lookback_window),
                    ),
                    config_start_date,
                )
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=datetime.timezone.utc)
        today = datetime.datetime.now(tz=start_date.tzinfo)
        end_date = min(start_date + datetime.timedelta(days=STEP_NUM_DAYS), today)
        params: dict[str, Any] = {
            "page_size": 100,
            "advertiser_id": self.primary_advertiser_id(),
            "store_ids": json.dumps([str(context["store_id"])]),
            "dimensions": json.dumps(REPORT_DIMENSIONS),
            "metrics": json.dumps(self.tiktok_metrics),
            "start_date": start_date.strftime(DATE_FORMAT),
            "end_date": end_date.strftime(DATE_FORMAT),
            "filtering": json.dumps(
                {"gmv_max_promotion_types": self.report_promotion_types}
            ),
        }
        if next_page_token and isinstance(next_page_token, dict) and next_page_token.get("page"):
            params["page"] = next_page_token["page"]
        return params

    def get_next_page_token(
        self, response: requests.Response, previous_token: Any | None
    ) -> Any | None:
        """Advance report pages within a date window, then move to the next window."""
        payload = response.json()
        current_page = self._get_page_info("$.data.page_info.page", payload) or 0
        total_pages = self._get_page_info("$.data.page_info.total_page", payload) or 0
        start_date = datetime.datetime.strptime(
            parse_qs(urlparse(response.request.url).query)["start_date"][0], DATE_FORMAT
        ).replace(tzinfo=datetime.timezone.utc)
        yesterday = datetime.datetime.now(tz=start_date.tzinfo) - datetime.timedelta(days=1)
        end_date = datetime.datetime.strptime(
            parse_qs(urlparse(response.request.url).query)["end_date"][0], DATE_FORMAT
        ).replace(tzinfo=datetime.timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=datetime.timezone.utc)
        prev_start = (
            previous_token.get("start_date")
            if isinstance(previous_token, dict)
            else None
        )
        if current_page < total_pages:
            return {"page": current_page + 1, "start_date": prev_start}
        if end_date.date() < yesterday.date():
            return {
                "page": 1,
                "start_date": min(
                    end_date + datetime.timedelta(days=1), yesterday
                ).strftime(DATE_FORMAT),
            }
        return None

    def request_records(self, context: dict | None) -> Iterable[dict]:
        """Paginate through report pages and date windows even when a window is empty."""
        if not self._store_reports_enabled(context):
            return
        next_page_token: Any = None
        finished = False
        decorated_request = self.request_decorator(self._request)

        while not finished:
            prepared_request = self.prepare_request(
                context, next_page_token=next_page_token
            )
            resp = decorated_request(prepared_request, context)
            yield from self.parse_response(resp)
            previous_token = copy.deepcopy(next_page_token)
            next_page_token = self.get_next_page_token(
                response=resp, previous_token=previous_token
            )
            if next_page_token and next_page_token == previous_token:
                raise RuntimeError(
                    "Loop detected in pagination. "
                    "Pagination token is identical to prior token."
                )
            finished = not next_page_token


def _report_schema(metric_names: list[str]) -> dict:
    """Build a Singer schema for a GMV Max campaign-level daily report stream."""
    dimension_fields = {"store_id", "advertiser_id", "campaign_id", "stat_time_day"}
    properties = [
        th.Property("store_id", th.StringType),
        th.Property("advertiser_id", th.StringType),
        th.Property("campaign_id", th.StringType),
        th.Property("stat_time_day", th.DateTimeType),
    ]
    properties += [
        th.Property(metric, th.StringType)
        for metric in metric_names
        if metric not in dimension_fields
    ]
    return th.PropertiesList(*properties).to_dict()


class GmvMaxProductCampaignMetricsByDayStream(GmvMaxCampaignMetricsByDayStream):
    """Product GMV Max campaign metrics by day for a TikTok Shop."""

    name = "gmv_max_product_campaign_metrics_by_day"
    parent_stream_type = GmvMaxStoresStream
    report_promotion_types = ["PRODUCT"]
    tiktok_metrics = PRODUCT_CAMPAIGN_REPORT_METRICS
    primary_keys = ["store_id", "campaign_id", "stat_time_day"]
    schema = _report_schema(PRODUCT_CAMPAIGN_REPORT_METRICS)


class GmvMaxLiveCampaignMetricsByDayStream(GmvMaxCampaignMetricsByDayStream):
    """LIVE GMV Max campaign metrics by day for a TikTok Shop."""

    name = "gmv_max_live_campaign_metrics_by_day"
    parent_stream_type = GmvMaxStoresStream
    report_promotion_types = ["LIVE"]
    tiktok_metrics = LIVE_CAMPAIGN_REPORT_METRICS
    primary_keys = ["store_id", "campaign_id", "stat_time_day"]
    schema = _report_schema(LIVE_CAMPAIGN_REPORT_METRICS)
