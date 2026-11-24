from services.price_service import (
    _parse_bitpin_prices,
    _parse_nobitex_v3_orderbook,
    _parse_wallex_coin_list,
    _parse_wallex_markets_usdttmn,
    round_to_nearest_10,
)


def test_nobitex_mid_price():
    data = {"status": "ok", "bids": [["1000", "1"]], "asks": [["1100", "1"]]}
    assert _parse_nobitex_v3_orderbook(data) == 1050.0


def test_nobitex_bad_payloads():
    assert _parse_nobitex_v3_orderbook({"status": "failed"}) is None
    assert _parse_nobitex_v3_orderbook({"status": "ok", "bids": [], "asks": []}) is None


def test_bitpin():
    assert _parse_bitpin_prices({"results": {"USDT_IRT": {"price": "123.5"}}}) == 123.5
    assert _parse_bitpin_prices({}) is None


def test_wallex_toman_is_converted_to_rial():
    data = {"result": {"coins": [{"key": "BTC", "price": "1"}, {"key": "usdt", "price": "60000"}]}}
    assert _parse_wallex_coin_list(data) == 600000.0
    markets = {"result": {"symbols": {"USDTTMN": {"stats": {"lastPrice": "60000"}}}}}
    assert _parse_wallex_markets_usdttmn(markets) == 600000.0
    assert _parse_wallex_markets_usdttmn({}) is None


def test_round_to_nearest_10():
    assert round_to_nearest_10(1234) == 1230
    assert round_to_nearest_10(1236) == 1240
