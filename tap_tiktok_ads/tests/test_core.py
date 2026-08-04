"""Tests standard tap features."""

import datetime

from tap_tiktok_ads.tap import TapTikTokAds

SAMPLE_CONFIG = {
    "access_token": "test-access-token",
    "advertiser_ids": ["1234567890"],
    "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
}


def test_tap_metadata():
    tap = TapTikTokAds(config=SAMPLE_CONFIG)
    assert tap.name == "tap-tiktok-ads"


def test_discover_streams():
    tap = TapTikTokAds(config=SAMPLE_CONFIG)
    streams = tap.discover_streams()
    assert len(streams) == 18
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
    }
