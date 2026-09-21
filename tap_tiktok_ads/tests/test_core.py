"""Tests standard tap features."""

import datetime

import pytest

from tap_tiktok_ads.tap import TapTikTokAds

SAMPLE_CONFIG = {
    "access_token": "test-access-token",
    "advertiser_ids": ["1234567890"],
    "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
}


def test_tap_metadata():
    tap = TapTikTokAds(config=SAMPLE_CONFIG)
    assert tap.name == "tap-tiktok-ads"


def test_advertiser_id_list_prefers_advertiser_id():
    tap = TapTikTokAds(
        config={
            **SAMPLE_CONFIG,
            "advertiser_id": "9999999999",
            "advertiser_ids": ["1234567890"],
        }
    )
    assert tap.advertiser_id_list == ["9999999999"]


def test_advertiser_id_list_falls_back_to_advertiser_ids():
    tap = TapTikTokAds(config=SAMPLE_CONFIG)
    assert tap.advertiser_id_list == ["1234567890"]


def test_advertiser_id_list_requires_advertiser_config():
    tap = TapTikTokAds(
        config={
            "access_token": SAMPLE_CONFIG["access_token"],
            "start_date": SAMPLE_CONFIG["start_date"],
        }
    )
    with pytest.raises(ValueError, match="advertiser_id"):
        tap.advertiser_id_list


def test_discover_streams():
    tap = TapTikTokAds(config=SAMPLE_CONFIG)
    streams = tap.discover_streams()
    assert len(streams) == 22
    assert {stream.name for stream in streams} == {
        "ad_accounts",
        "campaigns",
        "ad_groups",
        "ads",
        "ads_attribute_metrics",
        "ads_basic_data_metrics_by_day",
        "ads_video_play_metrics_by_day",
        "ads_engagement_metrics_by_day",
        "ads_attribution_metrics_by_day",
        "ads_page_event_metrics_by_day",
        "ads_in_app_event_metrics_by_day",
        "campaigns_attribute_metrics",
        "campaigns_basic_data_metrics_by_day",
        "campaigns_video_play_metrics_by_day",
        "campaigns_engagement_metrics_by_day",
        "campaigns_attribution_metrics_by_day",
        "campaigns_page_event_metrics_by_day",
        "campaigns_in_app_event_metrics_by_day",
        "gmv_max_stores",
        "gmv_max_campaigns",
        "gmv_max_product_campaign_metrics_by_day",
        "gmv_max_live_campaign_metrics_by_day",
    }
