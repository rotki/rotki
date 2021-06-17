import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import KRAKEN_TO_WORLD, asset_from_kraken
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
from rotkehlchen.errors import DeserializationError, UnknownAsset, UnprocessableTradePair
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.kraken import KRAKEN_DELISTED, Kraken, kraken_to_world_pair
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp_from_kraken
from rotkehlchen.tests.utils.constants import (
    A_AUD,
    A_CAD,
    A_CHF,
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
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetMovementCategory, Location
from rotkehlchen.utils.misc import ts_now


def test_name():
    exchange = Kraken('kraken1', 'a', b'a', object(), object())
    assert exchange.location == Location.KRAKEN
    assert exchange.name == 'kraken1'


def test_coverage_of_kraken_balances(kraken):
    got_assets = set(kraken.api_query('Assets').keys())
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


def test_querying_deposits_withdrawals(function_scope_kraken):
    now = ts_now()
    result = function_scope_kraken.query_deposits_withdrawals(
        start_ts=1451606400,
        end_ts=now,
        only_cache=False,
    )
    assert isinstance(result, list)
    assert len(result) != 0


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

    movements = kraken.query_deposits_withdrawals(
        start_ts=1408994442,
        end_ts=1498994442,
        only_cache=False,
    )

    assert len(movements) == 4
    assert movements[0].asset == A_BTC
    assert movements[0].amount == FVal('5.0')
    assert movements[0].category == AssetMovementCategory.DEPOSIT
    assert movements[1].asset == A_ETH
    assert movements[1].amount == FVal('10.0')
    assert movements[1].category == AssetMovementCategory.DEPOSIT
    assert movements[2].asset == A_BTC
    assert movements[2].amount == FVal('5.0')
    assert movements[2].category == AssetMovementCategory.WITHDRAWAL
    assert movements[3].asset == A_ETH
    assert movements[3].amount == FVal('10.0')
    assert movements[3].category == AssetMovementCategory.WITHDRAWAL

    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(warnings) == 2
    assert 'unknown kraken asset IDONTEXIST' in warnings[0]
    assert 'unknown kraken asset IDONTEXISTEITHER' in warnings[1]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_query_deposit_withdrawals_unexpected_data(function_scope_kraken):
    """Test if a kraken deposits_withdrawals query returns invalid data we handle it gracefully"""
    kraken = function_scope_kraken
    kraken.random_ledgers_data = False

    test_deposits = """{
    "ledger": {
    "1": {
    "refid": "1",
    "time": "1458994442",
    "type": "deposit",
    "aclass": "currency",
    "asset": "BTC",
    "amount": "5.0",
    "balance": "10.0",
    "fee": "0.1"
    }
    },
    "count": 1
    }"""

    withdraws = 'rotkehlchen.tests.utils.kraken.KRAKEN_SPECIFIC_WITHDRAWALS_RESPONSE'
    zero_withdraws = patch(withdraws, new='{"count": 0, "ledger":{}}')

    def query_kraken_and_test(
            input_ledger,
            expected_warnings_num,
            expected_errors_num,
            expect_skip=False,
    ):
        with patch(target, new=input_ledger), zero_withdraws:
            deposits = kraken.query_online_deposits_withdrawals(
                start_ts=0,
                end_ts=TEST_END_TS,
            )

        if not expect_skip and expected_warnings_num == 0 and expected_errors_num == 0:
            assert len(deposits) == 1
            assert deposits[0].category == AssetMovementCategory.DEPOSIT
            assert deposits[0].asset == A_BTC
        else:
            assert len(deposits) == 0
        errors = kraken.msg_aggregator.consume_errors()
        warnings = kraken.msg_aggregator.consume_warnings()
        assert len(errors) == expected_errors_num
        assert len(warnings) == expected_warnings_num

    # first normal deposit should have no problem
    target = 'rotkehlchen.tests.utils.kraken.KRAKEN_SPECIFIC_DEPOSITS_RESPONSE'
    query_kraken_and_test(test_deposits, expected_warnings_num=0, expected_errors_num=0)

    # From here and on let's make sure we react correctly to unexpected data
    # Invalid timestamp
    input_ledger = test_deposits
    input_ledger = input_ledger.replace('1458994442', 'dsadsadad')
    query_kraken_and_test(input_ledger, expected_warnings_num=0, expected_errors_num=1)

    # Invalid category type -- is skipped so no errors but a warning
    input_ledger = test_deposits
    input_ledger = input_ledger.replace('deposit', 'drinking')
    query_kraken_and_test(
        input_ledger,
        expected_warnings_num=0,
        expected_errors_num=0,
        expect_skip=True,
    )

    # Invalid asset type
    input_ledger = test_deposits
    input_ledger = input_ledger.replace('"BTC"', '[]')
    query_kraken_and_test(input_ledger, expected_warnings_num=0, expected_errors_num=1)

    # Unknown asset
    input_ledger = test_deposits
    input_ledger = input_ledger.replace('"BTC"', '"DSADSD"')
    query_kraken_and_test(input_ledger, expected_warnings_num=1, expected_errors_num=0)

    # Invalid amount
    input_ledger = test_deposits
    input_ledger = input_ledger.replace('"5.0"', 'null')
    query_kraken_and_test(input_ledger, expected_warnings_num=0, expected_errors_num=1)

    # Invalid fee
    input_ledger = test_deposits
    input_ledger = input_ledger.replace('"0.1"', '{}')
    query_kraken_and_test(input_ledger, expected_warnings_num=0, expected_errors_num=1)

    # Missing key entry
    input_ledger = test_deposits
    input_ledger = input_ledger.replace('"asset": "BTC",', '')
    query_kraken_and_test(input_ledger, expected_warnings_num=0, expected_errors_num=1)


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
        "trades": {
            "1": {
                "ordertxid": "1",
                "postxid": 1,
                "pair": "XXBTZEUR",
                "time": "1458994442.2353",
                "type": "buy",
                "ordertype": "market",
                "price": "100",
                "vol": "1",
                "fee": "0.1",
                "cost": "100",
                "margin": "0.0",
                "misc": ""
            }
        },
        "count": 1
    }"""

    def query_kraken_and_test(input_trades, expected_warnings_num, expected_errors_num):
        with patch(target, new=input_trades):
            trades = kraken.query_online_trade_history(
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
    target = 'rotkehlchen.tests.utils.kraken.KRAKEN_SPECIFIC_TRADES_HISTORY_RESPONSE'
    query_kraken_and_test(test_trades, expected_warnings_num=0, expected_errors_num=0)

    # Kraken also uses floats for timestamps, this should also work
    input_trades = test_trades
    input_trades = input_trades.replace('"time": "1458994442.2353"', '"time": 1458994442.2353')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=0)

    # From here and on let's check trades with unexpected data
    input_trades = test_trades
    input_trades = input_trades.replace('"pair": "XXBTZEUR"', '"pair": "aadda"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"time": "1458994442.2353"', '"time": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"vol": "1"', '"vol": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"cost": "100"', '"cost": null')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"fee": "0.1"', '"fee": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"type": "buy"', '"type": "not existing type"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"price": "100"', '"price": "dsadsda"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    # Also test key error
    input_trades = test_trades
    input_trades = input_trades.replace('"vol": "1",', '')
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
