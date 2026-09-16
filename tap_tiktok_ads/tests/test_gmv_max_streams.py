"""Tests for GMV Max streams."""

import datetime
import json
from unittest.mock import Mock
from tap_tiktok_ads.gmv_max_streams import (
    GmvMaxCampaignsStream,
    GmvMaxProductCampaignMetricsByDayStream,
    GmvMaxStoresStream,
)
from tap_tiktok_ads.tap import TapTikTokAds

SAMPLE_CONFIG = {
    "access_token": "test-access-token",
    "advertiser_ids": ["1234567890"],
    "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
}


def test_gmv_max_stores_child_context():
    stream = GmvMaxStoresStream(tap=TapTikTokAds(config=SAMPLE_CONFIG))
    ctx = stream.get_child_context(
        {"store_id": "store-001", "is_gmv_max_available": True},
        None,
    )
    assert ctx == {"store_id": "store-001", "is_gmv_max_available": True}


def test_gmv_max_campaigns_filtering():
    stream = GmvMaxCampaignsStream(tap=TapTikTokAds(config=SAMPLE_CONFIG))
    params = stream.get_url_params(None, None)
    filtering = json.loads(params["filtering"])
    assert filtering["gmv_max_promotion_types"] == ["PRODUCT_GMV_MAX", "LIVE_GMV_MAX"]
    assert params["advertiser_id"] == "1234567890"


def test_gmv_max_product_report_skips_unavailable_store():
    stream = GmvMaxProductCampaignMetricsByDayStream(tap=TapTikTokAds(config=SAMPLE_CONFIG))
    records = list(
        stream.get_records({"store_id": "1", "is_gmv_max_available": False})
    )
    assert records == []


def test_gmv_max_product_report_url_params():
    stream = GmvMaxProductCampaignMetricsByDayStream(tap=TapTikTokAds(config=SAMPLE_CONFIG))
    params = stream.get_url_params(
        {"store_id": "shop-99", "is_gmv_max_available": True},
        None,
    )
    assert params["store_ids"] == json.dumps(["shop-99"])
    assert json.loads(params["dimensions"]) == ["campaign_id", "stat_time_day"]
    filtering = json.loads(params["filtering"])
    assert filtering["gmv_max_promotion_types"] == ["PRODUCT"]
    assert "cost" in json.loads(params["metrics"])


def test_gmv_max_report_pagination_preserves_date_window():
    stream = GmvMaxProductCampaignMetricsByDayStream(tap=TapTikTokAds(config=SAMPLE_CONFIG))
    context = {"store_id": "shop-99", "is_gmv_max_available": True}
    first_params = stream.get_url_params(context, None)
    window_start = first_params["start_date"]
    window_end = first_params["end_date"]

    response = Mock()
    response.json.return_value = {
        "data": {"page_info": {"page": 1, "total_page": 2}},
    }
    response.request.url = (
        f"https://business-api.tiktok.com/open_api/v1.3/gmv_max/report/get/"
        f"?start_date={window_start}&end_date={window_end}"
    )

    page_token = stream.get_next_page_token(response, previous_token=None)
    assert page_token == {"page": 2, "start_date": window_start}

    second_params = stream.get_url_params(context, page_token)
    assert second_params["start_date"] == window_start
    assert second_params["end_date"] == window_end
    assert second_params["page"] == 2
