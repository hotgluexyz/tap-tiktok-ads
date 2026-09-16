"""TikTok tap class."""

from __future__ import annotations

from pathlib import PurePath
from typing import Any, cast

import requests
from hotglue_etl_exceptions import InvalidCredentialsError
from hotglue_singer_sdk import Stream, Tap
from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.exceptions import FatalAPIError
from hotglue_singer_sdk.helpers.capabilities import AlertingLevel

from tap_tiktok_ads.auth import TikTokAuthenticator
from tap_tiktok_ads.gmv_max_streams import (
    GmvMaxCampaignsStream,
    GmvMaxLiveCampaignMetricsByDayStream,
    GmvMaxProductCampaignMetricsByDayStream,
    GmvMaxStoresStream,
)
from tap_tiktok_ads.streams import (
    AdAccountsStream,
    AdGroupsStream,
    AdsAttributeMetricsStream,
    AdsAttributionMetricsByDayStream,
    AdsBasicDataMetricsByDayStream,
    AdsEngagementMetricsByDayStream,
    AdsInAppEventMetricsByDayStream,
    AdsPageEventMetricsByDayStream,
    AdsStream,
    AdsVideoPlayMetricsByDayStream,
    CampaignsAttributeMetricsStream,
    CampaignsAttributionMetricsByDayStream,
    CampaignsBasicDataMetricsByDayStream,
    CampaignsEngagementMetricsByDayStream,
    CampaignsInAppEventMetricsByDayStream,
    CampaignsPageEventMetricsByDayStream,
    CampaignsStream,
    CampaignsVideoPlayMetricsByDayStream,
)

GMV_MAX_STREAM_TYPES = [
    GmvMaxStoresStream,
    GmvMaxCampaignsStream,
    GmvMaxProductCampaignMetricsByDayStream,
    GmvMaxLiveCampaignMetricsByDayStream,
]

STREAM_TYPES = [
    AdAccountsStream,
    CampaignsStream,
    AdGroupsStream,
    AdsStream,
    AdsAttributeMetricsStream,
    AdsBasicDataMetricsByDayStream,
    AdsVideoPlayMetricsByDayStream,
    AdsEngagementMetricsByDayStream,
    AdsAttributionMetricsByDayStream,
    AdsPageEventMetricsByDayStream,
    AdsInAppEventMetricsByDayStream,
    CampaignsAttributeMetricsStream,
    CampaignsBasicDataMetricsByDayStream,
    CampaignsVideoPlayMetricsByDayStream,
    CampaignsEngagementMetricsByDayStream,
    CampaignsAttributionMetricsByDayStream,
    CampaignsPageEventMetricsByDayStream,
    CampaignsInAppEventMetricsByDayStream,
] + GMV_MAX_STREAM_TYPES


class TapTikTokAds(Tap):
    """TikTok tap class."""

    name = "tap-tiktok-ads"
    alerting_level = AlertingLevel.ERROR
    exception_alerting_level_map = {
        InvalidCredentialsError: AlertingLevel.NONE,
        FatalAPIError: AlertingLevel.NONE,
        requests.exceptions.RequestException: AlertingLevel.NONE,
    }

    @classmethod
    def access_token_support(cls, connector: Any = None) -> Any:
        return TikTokAuthenticator, None

    def __init__(
        self,
        config: dict[str, Any] | PurePath | str | list[PurePath | str] | None = None,
        catalog: Any = None,
        state: Any = None,
        parse_env_config: bool = False,
        validate_config: bool = True,
    ) -> None:
        if isinstance(config, list) and config and isinstance(config[0], str):
            self.config_file = config[0]
        super().__init__(config, catalog, state, parse_env_config, validate_config)

    config_jsonschema = th.PropertiesList(
        th.Property(
            "access_token",
            th.StringType,
            description="Access token for the TikTok Marketing API",
        ),
        th.Property(
            "advertiser_ids",
            th.ArrayType(th.StringType),
            description="Advertiser IDs to sync",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync",
        ),
        th.Property(
            "include_deleted",
            th.BooleanType,
            default=True,
            description="If true then deleted status entities will also be returned",
        ),
        th.Property(
            "lookback",
            th.IntegerType,
            default=14,
            description="Number of days of data to reload from the current date",
        ),
    ).to_dict()

    @property
    def advertiser_id_list(self) -> list[str]:
        return cast(dict[str, Any], self.config)["advertiser_ids"]

    def discover_streams(self) -> list[Stream]:
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


if __name__ == "__main__":
    TapTikTokAds.cli()
