from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.exchanges.bitcoinde import (
    BITCOINDE_TRADING_PAIRS,
    Bitcoinde,
    bitcoinde_pair_to_world,
)
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import Location, TradeType

BITCOINDE_BALANCES_RESPONSE = """{"data":{"balances":{"btc":{"total_amount":"0.5","available_amount":"0.5","reserved_amount":"0"},"bch":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"},"btg":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"},"eth":{"total_amount":"32.0","available_amount":"32.0","reserved_amount":"0"},"bsv":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"},"ltc":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"}},"encrypted_information":{"uid":"X","bic_short":"Y","bic_full":"Z"}},"errors":[],"credits":23}"""  # noqa: E501

BITCOINDE_TRADES_RESPONSE = """{"trades":[{"trade_id":"X1","trading_pair":"btceur","is_external_wallet_trade":false,"type":"buy","amount_currency_to_trade":"10","price":2312.23,"volume_currency_to_pay":2341.21,"volume_currency_to_pay_after_fee":124.241,"amount_currency_to_trade_after_fee":9.9,"fee_currency_to_pay":1.5214,"fee_currency_to_trade":"0.0324","created_at":"2017-12-06T02:02:32+01:00","successfully_finished_at":"2017-12-06T04:31:32+01:00","state":1,"is_trade_marked_as_paid ":true,"trade_marked_as_paid_at":"2017-12-06T08:15:42+01:00","payment_method":1,"my_rating_for_trading_partner":"positive","trading_partner_information":{"username":"USER1","is_kyc_full":true,"trust_level":"platin","amount_trades":31234123,"rating":2412,"bank_name":"FIDOR BANK AG","bic":"FDDODEMMXXX","seat_of_bank":"DE"}},{"trade_id":"X2","trading_pair":"btceur","is_external_wallet_trade":false,"type":"buy","amount_currency_to_trade":"241.214","price":214.124,"volume_currency_to_pay":4124.124,"volume_currency_to_pay_after_fee":2412.75,"amount_currency_to_trade_after_fee":0.512359,"fee_currency_to_pay":0.93452135,"fee_currency_to_trade":"0.0084512","created_at":"2017-08-09T22:21:07+02:00","successfully_finished_at":"2017-08-11T10:13:19+02:00","new_order_id_for_remaining_amount":"X3","state":1,"is_trade_marked_as_paid":true,"trade_marked_as_paid_at":"2017-08-09T16:40:23+02:00","payment_method":1,"my_rating_for_trading_partner":"positive","trading_partner_information":{"username":"USER2","is_kyc_full":true,"trust_level":"platin","amount_trades":2344,"rating":100,"bank_name":"FIDOR BANK AG","bic":"FDDODEMMXXX","seat_of_bank":"DE"}}],"page":{"current":1,"last":1},"errors":[],"credits":19}"""  # noqa: E501


def test_location():
    exchange = Bitcoinde('bitcoinde1', 'a', b'a', object(), object())
    assert exchange.location == Location.BITCOINDE
    assert exchange.name == 'bitcoinde1'


def test_bitcoinde_query_balances_unknown_asset(function_scope_bitcoinde):
    """Test that if a bitcoinde balance query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported assets"""
    bitcoinde = function_scope_bitcoinde

    def mock_unknown_asset_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, BITCOINDE_BALANCES_RESPONSE)

    with patch.object(bitcoinde.session, 'get', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = bitcoinde.query_balances()

    assert msg == ''
    assert len(balances) == 6
    assert balances[A_ETH].amount == FVal('32.0')
    assert balances[A_BTC].amount == FVal('0.5')

    warnings = bitcoinde.msg_aggregator.consume_warnings()
    assert len(warnings) == 0


def test_query_trade_history(function_scope_bitcoinde):
    """Happy path test for bitcoinde trade history querying"""
    bitcoinde = function_scope_bitcoinde

    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, BITCOINDE_TRADES_RESPONSE)

    with patch.object(bitcoinde.session, 'get', side_effect=mock_api_return):
        trades = bitcoinde.query_trade_history(
            start_ts=0,
            end_ts=1565732120,
            only_cache=False,
        )

    assert len(trades) == 2
    assert trades[0].timestamp == 1512531092
    assert trades[0].location == Location.BITCOINDE
    assert trades[0].base_asset == A_BTC
    assert trades[0].quote_asset == A_EUR
    assert trades[0].trade_type == TradeType.BUY
    assert trades[0].amount == FVal('10')
    assert trades[0].rate.is_close(FVal('234.121'))
    assert trades[0].fee.is_close(FVal('1.5214'))
    assert isinstance(trades[0].fee_currency, Asset)
    assert trades[0].fee_currency == A_EUR

    assert trades[1].timestamp == 1502439199
    assert trades[1].location == Location.BITCOINDE
    assert trades[1].base_asset == A_BTC
    assert trades[1].quote_asset == A_EUR
    assert trades[1].trade_type == TradeType.BUY
    assert trades[1].amount == FVal('241.214')
    assert trades[1].rate.is_close(FVal('17.09736582453754757186564627'))
    assert trades[1].fee.is_close(FVal('0.93452135'))
    assert isinstance(trades[1].fee_currency, Asset)
    assert trades[1].fee_currency == A_EUR


def test_bitcoinde_trading_pairs():
    for pair in BITCOINDE_TRADING_PAIRS:
        _ = bitcoinde_pair_to_world(pair)


def test_bitcoinde_invalid_trading_pair():
    with pytest.raises(UnknownAsset):
        _ = bitcoinde_pair_to_world('000btc')

    with pytest.raises(DeserializationError):
        _ = bitcoinde_pair_to_world('invalidpair')
