import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import KRAKEN_TO_WORLD, asset_from_kraken
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_ADA,
    A_BCH,
    A_BTC,
    A_DAI,
    A_ETH,
    A_ETH2,
    A_LTC,
    A_USD,
    A_USDT,
    A_XRP,
)
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.kraken import KRAKEN_DELISTED, Kraken
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp_from_kraken
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.constants import (
    A_AUD,
    A_CAD,
    A_CHF,
    A_DAO,
    A_DASH,
    A_EUR,
    A_EWT,
    A_GBP,
    A_JPY,
    A_OCEAN,
    A_QTUM,
    A_SC,
    A_WAVES,
    A_XTZ,
)
from rotkehlchen.tests.utils.exchanges import kraken_to_world_pair, try_get_first_exchange
from rotkehlchen.tests.utils.history import TEST_END_TS, prices
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.pnl_report import query_api_create_and_get_report
from rotkehlchen.types import AssetMovementCategory, Location, Timestamp, TradeType
from rotkehlchen.utils.misc import ts_now


def test_name():
    exchange = Kraken('kraken1', 'a', b'a', object(), object())
    assert exchange.location == Location.KRAKEN
    assert exchange.name == 'kraken1'


def test_coverage_of_kraken_balances(kraken):
    got_assets = set(kraken.online_api_query('Assets').keys())
    expected_assets = (set(KRAKEN_TO_WORLD.keys()) - set(KRAKEN_DELISTED))
    # Ignore the staking assets from the got assets
    got_assets.remove('XTZ.S')
    got_assets.remove('DOT.S')
    got_assets.remove('ATOM.S')
    got_assets.remove('EUR.M')
    got_assets.remove('USD.M')
    got_assets.remove('XBT.M')
    got_assets.remove('KSM.S')
    got_assets.remove('ETH2.S')
    got_assets.remove('KAVA.S')
    got_assets.remove('EUR.HOLD')
    got_assets.remove('USD.HOLD')
    got_assets.remove('FLOW.S')
    got_assets.remove('FLOWH.S')
    got_assets.remove('FLOWH')  # what is FLOWH?
    got_assets.remove('ADA.S')
    got_assets.remove('SOL.S')
    got_assets.remove('KSM.P')  # kusama bonded for parachains
    got_assets.remove('ALGO.S')
    got_assets.remove('DOT.P')
    got_assets.remove('MINA.S')
    got_assets.remove('TRX.S')
    got_assets.remove('LUNA.S')
    got_assets.remove('SCRT.S')
    got_assets.remove('MATIC.S')
    got_assets.remove('GBP.HOLD')
    got_assets.remove('CHF.HOLD')
    got_assets.remove('CAD.HOLD')
    got_assets.remove('AUD.HOLD')
    got_assets.remove('AED.HOLD')

    diff = expected_assets.symmetric_difference(got_assets)
    if len(diff) != 0:
        test_warnings.warn(UserWarning(
            f"Our known assets don't match kraken's assets. Difference: {diff}",
        ))
    else:
        # Make sure all assets are covered by our from and to functions
        for kraken_asset in got_assets:
            _ = asset_from_kraken(kraken_asset)

    # also check that staked assets are properly processed
    assert asset_from_kraken('XTZ.S') == Asset('XTZ')
    assert asset_from_kraken('EUR.M') == Asset('EUR')
    assert asset_from_kraken('ADA.S') == Asset('ADA')


def test_querying_balances(function_scope_kraken):
    result, error_or_empty = function_scope_kraken.query_balances()
    assert error_or_empty == ''
    assert isinstance(result, dict)
    for asset, entry in result.items():
        assert isinstance(asset, Asset)
        assert isinstance(entry, Balance)


def test_querying_trade_history(function_scope_kraken):
    kraken = function_scope_kraken
    kraken.random_ledgers_data = False
    now = ts_now()
    result = function_scope_kraken.query_trade_history(
        start_ts=1451606400,
        end_ts=now,
        only_cache=False,
    )
    assert isinstance(result, list)
    assert len(result) != 0

    for kraken_trade in result:
        assert isinstance(kraken_trade, Trade)


def test_querying_rate_limit_exhaustion(function_scope_kraken, database):
    """Test that if kraken api rates limit us we don't get stuck in an infinite loop
    and also that we return what we managed to retrieve until rate limit occured.

    Regression test for https://github.com/rotki/rotki/issues/3629
    """
    kraken = function_scope_kraken
    kraken.use_original_kraken = True
    kraken.reduction_every_secs = 0.05

    count = 0

    def mock_response(url, **kwargs):  # pylint: disable=unused-argument
        nonlocal count
        if 'Ledgers' in url:
            if count == 0:
                text = '{"result":{"ledger":{"L1":{"refid":"AOEXXV-61T63-AKPSJ0","time":1609950165.4497,"type":"trade","subtype":"","aclass":"currency","asset":"KFEE","amount":"0.00","fee":"1.145","balance":"0.00"},"L2":{"refid":"AOEXXV-61T63-AKPSJ0","time":1609950165.4492,"type":"trade","subtype":"","aclass":"currency","asset":"ZEUR","amount":"50","fee":"0.4429","balance":"500"},"L3":{"refid":"AOEXXV-61T63-AKPSJ0","time":1609950165.4486,"type":"trade","subtype":"","aclass":"currency","asset":"XETH","amount":"-0.1","fee":"0.0000000000","balance":1.1}},"count":2}}'  # noqa: E501
                count += 1
                return MockResponse(200, text)
            # else
            text = '{"result": "", "error": "EAPI Rate limit exceeded"}'
            count += 1
            return MockResponse(200, text)
        if 'AssetPairs' in url:
            dir_path = Path(__file__).resolve().parent.parent
            filepath = dir_path / 'data' / 'assets_kraken.json'
            with open(filepath) as f:
                return MockResponse(200, f.read())
        # else
        raise AssertionError(f'Unexpected url in kraken query: {url}')

    patch_kraken = patch.object(kraken.session, 'post', side_effect=mock_response)
    patch_retries = patch('rotkehlchen.exchanges.kraken.KRAKEN_QUERY_TRIES', new=2)
    patch_dividend = patch('rotkehlchen.exchanges.kraken.KRAKEN_BACKOFF_DIVIDEND', new=1)

    with ExitStack() as stack:
        stack.enter_context(gevent.Timeout(8))
        stack.enter_context(patch_retries)
        stack.enter_context(patch_dividend)
        stack.enter_context(patch_kraken)
        trades = kraken.query_trade_history(start_ts=0, end_ts=1638529919, only_cache=False)

    assert len(trades) == 1
    with database.conn.read_ctx() as cursor:
        from_ts, to_ts = database.get_used_query_range(cursor, 'kraken_trades_mockkraken')
    assert from_ts == 0
    assert to_ts == 1638529919, 'should have saved only until the last trades timestamp'


def test_querying_deposits_withdrawals(function_scope_kraken):
    kraken = function_scope_kraken
    kraken.random_ledgers_data = False
    now = ts_now()
    result = function_scope_kraken.query_deposits_withdrawals(
        start_ts=1439994442,
        end_ts=now,
        only_cache=False,
    )
    assert isinstance(result, list)
    assert len(result) == 5


def test_kraken_to_world_pair(kraken):
    """Kraken does not consistently list its pairs so test here that most pairs work

    For example ETH can be ETH or XETH, BTC can be XXBT or XBT
    """
    # Some standard tests that should always pass
    assert kraken_to_world_pair('QTUMXBT') == (A_QTUM, A_BTC)
    assert kraken_to_world_pair('ADACAD') == (A_ADA, A_CAD)
    assert kraken_to_world_pair('BCHUSD') == (A_BCH, A_USD)
    assert kraken_to_world_pair('DASHUSD') == (A_DASH, A_USD)
    assert kraken_to_world_pair('XTZETH') == (A_XTZ, A_ETH)
    assert kraken_to_world_pair('ETHDAI') == (A_ETH, A_DAI)
    assert kraken_to_world_pair('SCXBT') == (A_SC, A_BTC)
    assert kraken_to_world_pair('SCEUR') == (A_SC, A_EUR)
    assert kraken_to_world_pair('WAVESUSD') == (A_WAVES, A_USD)
    assert kraken_to_world_pair('XXBTZGBP.d') == (A_BTC, A_GBP)
    assert kraken_to_world_pair('ETHCHF') == (A_ETH, A_CHF)
    assert kraken_to_world_pair('XBTCHF') == (A_BTC, A_CHF)
    assert kraken_to_world_pair('EURCAD') == (A_EUR, A_CAD)
    assert kraken_to_world_pair('USDCHF') == (A_USD, A_CHF)
    assert kraken_to_world_pair('EURJPY') == (A_EUR, A_JPY)
    assert kraken_to_world_pair('LTCETH') == (A_LTC, A_ETH)
    assert kraken_to_world_pair('LTCUSDT') == (A_LTC, A_USDT)
    assert kraken_to_world_pair('XRPGBP') == (A_XRP, A_GBP)
    assert kraken_to_world_pair('XRPUSDT') == (A_XRP, A_USDT)
    assert kraken_to_world_pair('AUDJPY') == (A_AUD, A_JPY)
    assert kraken_to_world_pair('ETH2.SETH') == (A_ETH2, A_ETH)
    assert kraken_to_world_pair('EWTEUR') == (A_EWT, A_EUR)
    assert kraken_to_world_pair('EWTGBP') == (A_EWT, A_GBP)
    assert kraken_to_world_pair('EWTXBT') == (A_EWT, A_BTC)
    assert kraken_to_world_pair('OCEANEUR') == (A_OCEAN, A_EUR)
    assert kraken_to_world_pair('OCEANGBP') == (A_OCEAN, A_GBP)
    assert kraken_to_world_pair('OCEANUSD') == (A_OCEAN, A_USD)
    assert kraken_to_world_pair('OCEANXBT') == (A_OCEAN, A_BTC)

    # now try to test all pairs that kraken returns and if one does not work note
    # down a test warning so that it can be fixed by us later
    pairs = kraken.api_query('AssetPairs').keys()
    for pair in pairs:
        try:
            kraken_to_world_pair(pair)
        except (UnknownAsset, UnprocessableTradePair, DeserializationError) as e:
            test_warnings.warn(UserWarning(
                f'Could not process kraken pair {pair} due to {str(e)}',
            ))

    # Finally test that wrong pairs raise proper exception
    with pytest.raises(UnprocessableTradePair):
        kraken_to_world_pair('GABOOBABOO')


def test_kraken_query_balances_unknown_asset(function_scope_kraken):
    """Test that if a kraken balance query returns unknown asset no exception
    is raised and a warning is generated"""
    kraken = function_scope_kraken
    kraken.random_balance_data = False
    balances, msg = kraken.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC].amount == FVal('5.0')
    assert balances[A_BTC].usd_value == FVal('7.5')
    assert balances[A_ETH].amount == FVal('10.0')
    assert balances[A_ETH].usd_value == FVal('15.0')

    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'unsupported/unknown kraken asset NOTAREALASSET' in warnings[0]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_query_deposit_withdrawals_unknown_asset(function_scope_kraken):
    """Test that if a kraken deposits_withdrawals query returns unknown asset
    no exception is raised and a warning is generated and the deposits/withdrawals
    with valid assets are still returned"""
    kraken = function_scope_kraken
    kraken.random_ledgers_data = False

    input_ledger = """
    {
    "ledger": {
        "0": {
            "refid": "2",
            "time": 1439994442,
            "type": "withdrawal",
            "subtype": "",
            "aclass": "currency",
            "asset": "XETH",
            "amount": "-1.0000000000",
            "fee": "0.0035000000",
            "balance": "0.0000100000"
        },
        "L12382343902": {
            "refid": "0",
            "time": 1458994441.396,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "EUR.HOLD",
            "amount": "4000000.0000",
            "fee": "1.7500",
            "balance": "3999998.25"
        },
        "L12382343903": {
            "refid": "3",
            "time": 1458994441.396,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "YYYYYYYYYYYY",
            "amount": "4000000.0000",
            "fee": "1.7500",
            "balance": "3999998.25"
        }
    },
        "count": 3
    }
    """

    target = 'rotkehlchen.tests.utils.kraken.KRAKEN_GENERAL_LEDGER_RESPONSE'
    with patch(target, new=input_ledger):
        movements = kraken.query_deposits_withdrawals(
            start_ts=1408994442,
            end_ts=1498994442,
            only_cache=False,
        )

    # first normal deposit should have no problem
    assert len(movements) == 2
    assert movements[0].asset == A_EUR
    assert movements[0].amount == FVal('4000000')
    assert movements[0].category == AssetMovementCategory.DEPOSIT
    assert movements[1].asset == A_ETH
    assert movements[1].amount == FVal('1')
    assert movements[1].category == AssetMovementCategory.WITHDRAWAL
    errors = kraken.msg_aggregator.consume_errors()
    assert len(errors) == 1


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_trade_with_spend_receive(function_scope_kraken):
    """Test that trades based on spend/receive events are correctly processed"""
    kraken = function_scope_kraken
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.cache_ttl_secs = 0

    test_trades = """{
        "ledger": {
            "L2": {
                "refid": "1",
                "time": 1636406000.8555,
                "type": "receive",
                "subtype": "",
                "aclass": "currency",
                "asset": "XETH",
                "amount": "1",
                "fee": "0.0000000000",
                "balance": "1001"
            },
            "L1": {
                "refid": "1",
                "time": 1636406000.8654,
                "type": "spend",
                "subtype": "",
                "aclass": "currency",
                "asset": "ZEUR",
                "amount": "-100",
                "fee": "0.4500",
                "balance": "30000000"
            }
        },
        "count": 2
    }"""

    target = 'rotkehlchen.tests.utils.kraken.KRAKEN_GENERAL_LEDGER_RESPONSE'
    with patch(target, new=test_trades):
        trades, _ = kraken.query_online_trade_history(
            start_ts=0,
            end_ts=Timestamp(1637406001),
        )

    assert len(trades) == 1
    trade = trades[0]
    assert trade.amount == ONE
    assert trade.trade_type == TradeType.BUY
    assert trade.rate == FVal(100)
    assert trade.base_asset == A_ETH
    assert trade.quote_asset == A_EUR
    assert trade.fee == FVal(0.45)
    errors = kraken.msg_aggregator.consume_errors()
    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_trade_with_adjustment(function_scope_kraken):
    """Test that trades based on adjustment events are processed"""
    kraken = function_scope_kraken
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.cache_ttl_secs = 0

    test_trades = """{
        "ledger": {
            "L1": {
                "refid": "1",
                "time": 1636406000.8555,
                "type": "adjustment",
                "subtype": "",
                "aclass": "currency",
                "asset": "XDAO",
                "amount": "-0.0008854800",
                "fee": "0.0000000000",
                "balance": "1"
            },
            "L2": {
                "refid": "2",
                "time": 1636406000.8654,
                "type": "adjustment",
                "subtype": "",
                "aclass": "currency",
                "asset": "XETH",
                "amount": "0.0000088548",
                "fee": "0",
                "balance": "1"
            }
        },
        "count": 2
    }"""

    target = 'rotkehlchen.tests.utils.kraken.KRAKEN_GENERAL_LEDGER_RESPONSE'
    with patch(target, new=test_trades):
        trades, _ = kraken.query_online_trade_history(
            start_ts=0,
            end_ts=Timestamp(1637406001),
        )

    assert len(trades) == 1
    trade = trades[0]
    assert trade.amount == FVal('0.0000088548')
    assert trade.trade_type == TradeType.BUY
    assert trade.rate == FVal('0.01')
    assert trade.base_asset == A_ETH
    assert trade.quote_asset == A_DAO
    assert trade.fee is None
    errors = kraken.msg_aggregator.consume_errors()
    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_trade_no_counterpart(function_scope_kraken):
    """Test that trades with no counterpart are processed properly"""
    kraken = function_scope_kraken
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.cache_ttl_secs = 0

    test_trades = """{
        "ledger": {
            "L1": {
                "refid": "1",
                "time": 1636406000.8555,
                "type": "trade",
                "subtype": "",
                "aclass": "currency",
                "asset": "XETH",
                "amount": "-0.000001",
                "fee": "0.0000000000",
                "balance": "1"
            },
            "L2": {
                "refid": "2",
                "time": 1636406000.8654,
                "type": "trade",
                "subtype": "",
                "aclass": "currency",
                "asset": "XXBT",
                "amount": "0.0000001",
                "fee": "0",
                "balance": "1"
            }
        },
        "count": 2
    }"""

    target = 'rotkehlchen.tests.utils.kraken.KRAKEN_GENERAL_LEDGER_RESPONSE'
    with patch(target, new=test_trades):
        trades, _ = kraken.query_online_trade_history(
            start_ts=0,
            end_ts=Timestamp(1637406001),
        )

    assert len(trades) == 2
    trade = trades[0]
    assert trade.amount == FVal('0.000001')
    assert trade.trade_type == TradeType.SELL
    assert trade.rate == ZERO
    assert trade.base_asset == A_ETH
    assert trade.quote_asset == A_USD
    assert trade.fee is None
    assert trade.fee_currency is None
    trade = trades[1]
    assert trade.amount == FVal('0.0000001')
    assert trade.trade_type == TradeType.BUY
    assert trade.rate == ZERO
    assert trade.base_asset == A_BTC
    assert trade.quote_asset == A_USD
    assert trade.fee is None
    assert trade.fee_currency is None
    errors = kraken.msg_aggregator.consume_errors()
    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_trade_from_kraken_unexpected_data(function_scope_kraken):
    """Test that getting unexpected data from kraken leads to skipping the trade
    and does not lead to a crash"""
    kraken = function_scope_kraken
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.cache_ttl_secs = 0

    # Important: Testing with a time floating point that has other than zero after decimal
    test_trades = """{
    "ledger": {
        "L343242342": {
            "refid": "1",
            "time": 1458994442.064,
            "type": "trade",
            "subtype": "",
            "aclass": "currency",
            "asset": "XXBT",
            "amount": "1",
            "fee": "0.0000000000",
            "balance": "0.0437477300"
            },
        "L5354645643": {
            "refid": "1",
            "time": 1458994442.063,
            "type": "trade",
            "subtype": "",
            "aclass": "currency",
            "asset": "ZEUR",
            "amount": "-100",
            "fee": "0.1",
            "balance": "200"
        }
    },
    "count": 2
}"""

    def query_kraken_and_test(input_trades, expected_warnings_num, expected_errors_num):
        # delete kraken history entries so they get requeried
        cursor = kraken.history_events_db.db.conn.cursor()
        with kraken.history_events_db.db.user_write() as cursor:
            location = Location.KRAKEN
            cursor.execute(
                'DELETE FROM history_events WHERE location=?',
                (location.serialize_for_db(),),
            )
            cursor.execute(
                'DELETE FROM used_query_ranges WHERE name LIKE ?',
                (f'{location}_history_events_%',),
            )

        with patch(target, new=input_trades):
            trades, _ = kraken.query_online_trade_history(
                start_ts=0,
                end_ts=TEST_END_TS,
            )

        if expected_warnings_num == 0 and expected_errors_num == 0:
            assert len(trades) == 1
            assert trades[0].base_asset == A_BTC
            assert trades[0].quote_asset == A_EUR
        else:
            assert len(trades) == 0
        errors = kraken.msg_aggregator.consume_errors()
        warnings = kraken.msg_aggregator.consume_warnings()
        assert len(errors) == expected_errors_num
        assert len(warnings) == expected_warnings_num

    # First a normal trade should have no problems
    target = 'rotkehlchen.tests.utils.kraken.KRAKEN_GENERAL_LEDGER_RESPONSE'
    query_kraken_and_test(test_trades, expected_warnings_num=0, expected_errors_num=0)

    # Kraken also uses strings for timestamps, this should also work
    input_trades = test_trades
    input_trades = input_trades.replace('"time": 1458994442.063', '"time": "1458994442.063"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=0)

    # From here and on let's check trades with unexpected data
    input_trades = test_trades
    input_trades = input_trades.replace('"asset": "XXBT"', '"asset": "lefty"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"time": 1458994442.063', '"time": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"amount": "1"', '"amount": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"amount": "-100"', '"amount": null')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"fee": "0.1"', '"fee": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    # Also test key error
    input_trades = test_trades
    input_trades = input_trades.replace('"amount": "-100",', '')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)


def test_emptry_kraken_balance_response():
    """Balance api query returns a response without a result

    Regression test for: https://github.com/rotki/rotki/issues/2443
    """
    kraken = Kraken('kraken1', 'a', b'YW55IGNhcm5hbCBwbGVhc3VyZS4=', object(), object())

    def mock_post(url, data, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, '{"error":[]}')

    with patch.object(kraken.session, 'post', wraps=mock_post):
        result, msg = kraken.query_balances()
        assert msg == ''
        assert result == {}


def test_timestamp_deserialization():
    """Test the function that allows to deserialize timestamp from different types"""
    assert deserialize_timestamp_from_kraken("1458994442.2353") == 1458994442
    assert deserialize_timestamp_from_kraken(1458994442.2353) == 1458994442
    assert deserialize_timestamp_from_kraken(1458994442) == 1458994442
    assert deserialize_timestamp_from_kraken(FVal(1458994442.2353)) == 1458994442
    with pytest.raises(DeserializationError):
        deserialize_timestamp_from_kraken("234a")
    with pytest.raises(DeserializationError):
        deserialize_timestamp_from_kraken("")


@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN,)])
@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('start_with_valid_premium', [False, True])
def test_kraken_staking(rotkehlchen_api_server_with_exchanges, start_with_valid_premium):
    """Test that kraken staking events are processed correctly"""
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    # The input has extra information to test that the filters work correctly.
    # The events related to staking are AAA, BBB and CCC, DDD
    input_ledger = """
    {
    "ledger":{
        "WWW": {
            "refid": "WWWWWWW",
            "time": 1640493376.4008,
            "type": "staking",
            "subtype": "",
            "aclass": "currency",
            "asset": "XTZ",
            "amount": "0.0000100000",
            "fee": "0.0000000000",
            "balance": "0.0000100000"
        },
        "AAA": {
            "refid": "XXXXXX",
            "time": 1640493374.4008,
            "type": "staking",
            "subtype": "",
            "aclass": "currency",
            "asset": "ETH2",
            "amount": "0.0000538620",
            "fee": "0.0000000000",
            "balance": "0.0003349820"
        },
        "BBB": {
            "refid": "YYYYYYYY",
            "time": 1636740198.9674,
            "type": "transfer",
            "subtype": "stakingfromspot",
            "aclass": "currency",
            "asset": "ETH2.S",
            "amount": "0.0600000000",
            "fee": "0.0000000000",
            "balance": "0.0600000000"
        },
        "CCC": {
            "refid": "ZZZZZZZZZ",
            "time": 1636738550.7562,
            "type": "transfer",
            "subtype": "spottostaking",
            "aclass": "currency",
            "asset": "XETH",
            "amount": "-0.0600000000",
            "fee": "0.0000000000",
            "balance": "0.0250477300"
        },
        "L12382343902": {
            "refid": "0",
            "time": 1458994441.396,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "EUR.HOLD",
            "amount": "4000000.0000",
            "fee": "1.7500",
            "balance": "3999998.25"
        },
        "DDD": {
            "refid": "DDDDD",
            "time": 1628994441.4008,
            "type": "staking",
            "subtype": "",
            "aclass": "currency",
            "asset": "ETH2",
            "amount": "12",
            "fee": "0",
            "balance": "0.1000538620"
        }
    },
    "count": 6
    }
    """
    # Test that before populating we don't have any event
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert len(result['events']) == 0

    with rotki.data.db.user_write() as cursor:
        rotki.data.db.purge_exchange_data(cursor, Location.KRAKEN)
        target = 'rotkehlchen.tests.utils.kraken.KRAKEN_GENERAL_LEDGER_RESPONSE'
        kraken = try_get_first_exchange(rotki.exchange_manager, Location.KRAKEN)
        kraken.random_ledgers_data = False
        with patch(target, new=input_ledger):
            kraken.query_kraken_ledgers(
                cursor=cursor,
                start_ts=1458984441,
                end_ts=1736738550,
            )

    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            "from_timestamp": 1636538550,
            "to_timestamp": 1640493378,
        },
    )

    result = assert_proper_response_with_result(response)
    events = result['events']

    assert len(events) == 3
    assert len(events) == result['entries_found']
    assert events[0]['event_type'] == 'reward'
    assert events[1]['event_type'] == 'reward'
    assert events[2]['event_type'] == 'deposit asset'
    assert events[0]['asset'] == 'XTZ'
    assert events[1]['asset'] == 'ETH2'
    assert events[2]['asset'] == 'ETH'
    assert events[0]['usd_value'] == '0.000046300000'
    assert events[1]['usd_value'] == '0.219353533620'
    assert events[2]['usd_value'] == '242.570400000000'
    if start_with_valid_premium:
        assert result['entries_limit'] == -1
    else:
        assert result['entries_limit'] == FREE_HISTORY_EVENTS_LIMIT
    assert result['entries_total'] == 4
    assert result['received'] == [
        {'asset': 'ETH2', 'amount': '0.000053862', 'usd_value': '0.21935353362'},
        {'asset': 'XTZ', 'amount': '0.00001', 'usd_value': '0.0000463'},
    ]

    # test that the correct number of entries is returned with pagination
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'from_timestamp': 1636738551,
            'to_timestamp': 1640493375,
            'limit': 1,
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 1
    assert set(result['assets']) == {'ETH', 'ETH2', 'XTZ'}

    # assert that filter by asset is working properly
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            "from_timestamp": 1628994442,
            "to_timestamp": 1640493377,
            "asset": "ETH2",
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result['events']) == 1
    assert len(result['received']) == 1

    # test that we can correctly query subtypes
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            "from_timestamp": 1458994441,
            "to_timestamp": 1640493377,
            "event_subtypes": ['reward'],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result['events']) == 3

    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            "from_timestamp": 1458994441,
            "to_timestamp": 1640493377,
            "event_subtypes": [
                'reward',
                'deposit asset',
            ],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result['events']) == 4

    # test that sorting for a non existing column is handled correctly
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            "ascending": [False],
            "async_query": False,
            "limit": 10,
            "offset": 0,
            "only_cache": True,
            "order_by_attributes": ["random_column"],
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Database query error retrieving misssing prices no such column',
        status_code=HTTPStatus.CONFLICT,
    )

    # test that the event_type filter for order attribute
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            "ascending": [False],
            "async_query": False,
            "limit": 10,
            "offset": 0,
            "only_cache": True,
            "order_by_attributes": ["event_type"],
        },
    )
    assert_proper_response_with_result(response)

    _, without_eth2_staking_report_result, _ = query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=0,
        end_ts=1640493377,
        prepare_mocks=False,
    )
    without_eth2_staking_overview = without_eth2_staking_report_result['entries'][0]['overview']
    assert FVal('39102.819423433620').is_close(
        FVal(without_eth2_staking_overview.get(str(AccountingEventType.STAKING))['taxable']),
    )
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.set_settings(
            cursor,
            ModifiableDBSettings(eth_staking_taxable_after_withdrawal_enabled=True),
        )
    _, with_eth2_staking_report_result, _ = query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=0,
        end_ts=1640493377,
        prepare_mocks=False,
    )
    with_eth2_staking_overview = with_eth2_staking_report_result['entries'][0]['overview']
    assert FVal('0.000069900000').is_close(
        FVal(with_eth2_staking_overview.get(str(AccountingEventType.STAKING))['taxable']),
    )
