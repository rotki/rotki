from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.bitcoinde import (
    Bitcoinde,
    bitcoinde_pair_to_world,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp, TimestampMS

BITCOINDE_BALANCES_RESPONSE = """{"data":{"balances":{"btc":{"total_amount":"0.5","available_amount":"0.5","reserved_amount":"0"},"bch":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"},"btg":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"},"eth":{"total_amount":"32.0","available_amount":"32.0","reserved_amount":"0"},"bsv":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"},"ltc":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"}},"encrypted_information":{"uid":"X","bic_short":"Y","bic_full":"Z"}},"errors":[],"credits":23}"""  # noqa: E501

BITCOINDE_TRADES_RESPONSE = """{"trades":[{"trade_id":"X1","trading_pair":"btceur","is_external_wallet_trade":false,"type":"buy","amount_currency_to_trade":"10","price":2312.23,"volume_currency_to_pay":2341.21,"volume_currency_to_pay_after_fee":124.241,"amount_currency_to_trade_after_fee":9.9,"fee_currency_to_pay":1.5214,"fee_currency_to_trade":"0.0324","created_at":"2017-12-06T02:02:32+01:00","successfully_finished_at":"2017-12-06T04:31:32+01:00","state":1,"is_trade_marked_as_paid ":true,"trade_marked_as_paid_at":"2017-12-06T08:15:42+01:00","payment_method":1,"my_rating_for_trading_partner":"positive","trading_partner_information":{"username":"USER1","is_kyc_full":true,"trust_level":"platin","amount_trades":31234123,"rating":2412,"bank_name":"FIDOR BANK AG","bic":"FDDODEMMXXX","seat_of_bank":"DE"}},{"trade_id":"X2","trading_pair":"btceur","is_external_wallet_trade":false,"type":"buy","amount_currency_to_trade":"241.214","price":214.124,"volume_currency_to_pay":4124.124,"volume_currency_to_pay_after_fee":2412.75,"amount_currency_to_trade_after_fee":0.512359,"fee_currency_to_pay":0.93452135,"fee_currency_to_trade":"0.0084512","created_at":"2017-08-09T22:21:07+02:00","successfully_finished_at":"2017-08-11T10:13:19+02:00","new_order_id_for_remaining_amount":"X3","state":1,"is_trade_marked_as_paid":true,"trade_marked_as_paid_at":"2017-08-09T16:40:23+02:00","payment_method":1,"my_rating_for_trading_partner":"positive","trading_partner_information":{"username":"USER2","is_kyc_full":true,"trust_level":"platin","amount_trades":2344,"rating":100,"bank_name":"FIDOR BANK AG","bic":"FDDODEMMXXX","seat_of_bank":"DE"}}],"page":{"current":1,"last":1},"errors":[],"credits":19}"""  # noqa: E501


# Pairs can be found in Basic API doc https://www.bitcoin.de/en/api/basic. There is no api to
# query these pairs.
BITCOINDE_TRADING_PAIRS = (
    'btceur',
    'bcheur',
    'btgeur',
    'etheur',
    'bsveur',
    'ltceur',
    'usdteur',
    'xrpeur',
    'dogeeur',
    'soleur',
    'trxeur',
    'iotabtc',  # not listed anymore
    'dashbtc',  # not listed anymore
    'gntbtc',  # not listed anymore
    'ltcbtc',  # not listed anymore
)


def test_location():
    exchange = Bitcoinde('bitcoinde1', 'a', b'a', object(), object())
    assert exchange.location == Location.BITCOINDE
    assert exchange.name == 'bitcoinde1'


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_bitcoinde_query_balances_unknown_asset(function_scope_bitcoinde):
    """Test that if a bitcoinde balance query returns unknown asset no exception
    is raised and a message is sent to the frontend."""
    bitcoinde = function_scope_bitcoinde

    def mock_unknown_asset_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, BITCOINDE_BALANCES_RESPONSE.replace('btc', 'abcdef'))

    with patch.object(bitcoinde.session, 'get', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = bitcoinde.query_balances()

    assert msg == ''
    assert len(balances) == 5
    assert balances[A_ETH].amount == FVal('32.0')
    assert len(bitcoinde.msg_aggregator.rotki_notifier.messages) == 1


def test_query_trade_history(function_scope_bitcoinde):
    """Happy path test for bitcoinde trade history querying"""
    bitcoinde = function_scope_bitcoinde

    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, BITCOINDE_TRADES_RESPONSE)

    with patch.object(bitcoinde.session, 'get', side_effect=mock_api_return):
        events, _ = bitcoinde.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1565732120),
        )

    assert events == [SwapEvent(
        timestamp=TimestampMS(1512531092000),
        location=Location.BITCOINDE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        amount=FVal('2341.21'),
        location_label='bitcoinde',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITCOINDE,
            unique_id='X1',
        ),
    ), SwapEvent(
        timestamp=TimestampMS(1512531092000),
        location=Location.BITCOINDE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('10'),
        location_label='bitcoinde',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITCOINDE,
            unique_id='X1',
        ),
    ), SwapEvent(
        timestamp=TimestampMS(1512531092000),
        location=Location.BITCOINDE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_EUR,
        amount=FVal('1.5214'),
        location_label='bitcoinde',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITCOINDE,
            unique_id='X1',
        ),
    ), SwapEvent(
        timestamp=TimestampMS(1502439199000),
        location=Location.BITCOINDE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        amount=FVal('4124.124'),
        location_label='bitcoinde',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITCOINDE,
            unique_id='X2',
        ),
    ), SwapEvent(
        timestamp=TimestampMS(1502439199000),
        location=Location.BITCOINDE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('241.214'),
        location_label='bitcoinde',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITCOINDE,
            unique_id='X2',
        ),
    ), SwapEvent(
        timestamp=TimestampMS(1502439199000),
        location=Location.BITCOINDE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_EUR,
        amount=FVal('0.93452135'),
        location_label='bitcoinde',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITCOINDE,
            unique_id='X2',
        ),
    )]


def test_bitcoinde_trading_pairs():
    for pair in BITCOINDE_TRADING_PAIRS:
        _ = bitcoinde_pair_to_world(pair)


def test_bitcoinde_invalid_trading_pair():
    with pytest.raises(UnknownAsset):
        _ = bitcoinde_pair_to_world('000btc')

    with pytest.raises(DeserializationError):
        _ = bitcoinde_pair_to_world('invalidpair')
