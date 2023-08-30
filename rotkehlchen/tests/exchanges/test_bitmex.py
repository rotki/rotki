from unittest.mock import patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.exchanges.bitmex import Bitmex
from rotkehlchen.exchanges.data_structures import AssetMovement, Location, MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import AssetMovementCategory
from rotkehlchen.utils.misc import ts_now


def test_name():
    exchange = Bitmex('bitmex1', 'a', b'a', object(), object())
    assert exchange.location == Location.BITMEX
    assert exchange.name == 'bitmex1'


def test_bitmex_api_signature(mock_bitmex):
    # tests cases from here: https://www.bitmex.com/app/apiKeysUsage
    sig = mock_bitmex._generate_signature(
        'get',
        '/api/v1/instrument',
        1518064236,
    )
    assert sig == 'c7682d435d0cfe87c16098df34ef2eb5a549d4c5a3c2b1f0f77b8af73423bf00'
    sig = mock_bitmex._generate_signature(
        'get',
        '/api/v1/instrument?filter=%7B%22symbol%22%3A+%22XBTM15%22%7D',
        1518064237,
    )
    assert sig == 'e2f422547eecb5b3cb29ade2127e21b858b235b386bfa45e1c1756eb3383919f'
    sig = mock_bitmex._generate_signature(
        'post',
        '/api/v1/order',
        1518064238,
        data=(
            '{"symbol":"XBTM15","price":219.0,'
            '"clOrdID":"mm_bitmex_1a/oemUeQ4CAJZgP3fjHsA","orderQty":98}'
        ),
    )
    assert sig == '1749cd2ccae4aa49048ae09f0b95110cee706e0944e6a14ad0b3a8cb45bd336b'


def test_bitmex_api_withdrawals_deposit_and_query_after_subquery(sandbox_bitmex):
    """Test the happy case of bitmex withdrawals deposit query

    This test also tests an important case where a subquery for a an in-between
    time range is done first and then an encompassing range is requested. And
    we test that the full query, queries the remaining timestamp ranges.
    """
    # This is an initial subquery of a small range where no deposit happened.
    result = sandbox_bitmex.query_deposits_withdrawals(
        start_ts=1536492800,
        end_ts=1536492976,
        only_cache=False,
    )
    assert len(result) == 0

    # Now after the subquery we test that the exchange engine logic properly
    # queries the required start/end timestamp ranges
    now = ts_now()
    result = sandbox_bitmex.query_deposits_withdrawals(
        start_ts=0,
        end_ts=now,
        only_cache=False,
    )
    expected_result = [
        AssetMovement(
            location=Location.BITMEX,
            category=AssetMovementCategory.DEPOSIT,
            address=None,
            transaction_id=None,
            timestamp=1536486278,
            asset=A_BTC,
            amount=FVal('0.46966992'),
            fee_asset=A_BTC,
            fee=ZERO,
            link='166b9aac-70ac-cedc-69a0-dbd12c0661bf',
        ),
        AssetMovement(
            location=Location.BITMEX,
            category=AssetMovementCategory.DEPOSIT,
            address=None,
            transaction_id=None,
            timestamp=1537014656,
            asset=A_BTC,
            amount=FVal(0.16960386),
            fee_asset=A_BTC,
            fee=FVal(0E-8),
            link='b6c6fd2c-4d0c-b101-a41c-fa5aa1ce7ef1',
        ),
        AssetMovement(
            location=Location.BITMEX,
            category=AssetMovementCategory.DEPOSIT,
            address=None,
            transaction_id=None,
            timestamp=1536563759,
            asset=A_BTC,
            amount=FVal('0.38474377'),
            fee_asset=A_BTC,
            fee=ZERO,
            link='72500751-d052-5bbb-18d7-08363edef812',
        ),
        AssetMovement(
            location=Location.BITMEX,
            category=AssetMovementCategory.WITHDRAWAL,
            address='mv4rnyY3Su5gjcDNzbMLKBQkBicCtHUtFB',
            transaction_id=None,
            timestamp=1536536707,
            asset=A_BTC,
            amount=FVal('0.00700000'),
            fee_asset=A_BTC,
            fee=FVal('0.00300000'),
            link='bf19ca4e-e084-11f9-12cd-6ae41e26f9db',
        ),
    ]
    assert result == expected_result
    # also make sure that asset movements contain Asset and not strings
    for movement in result:
        assert isinstance(movement.asset, Asset)


def test_bitmex_api_withdrawals_deposit_unexpected_data(sandbox_bitmex):
    """Test getting unexpected data in bitmex withdrawals deposit query is handled gracefully"""

    original_input = """[{
"transactID": "b6c6fd2c-4d0c-b101-a41c-fa5aa1ce7ef1", "account": 126541, "currency": "XBt",
 "transactType": "Withdrawal", "amount": 16960386, "fee": 800, "transactStatus": "Completed",
 "address": "", "tx": "", "text": "", "transactTime": "2018-09-15T12:30:56.475Z",
 "walletBalance": 103394923, "marginBalance": null,
 "timestamp": "2018-09-15T12:30:56.475Z"}]"""
    now = ts_now()

    def query_bitmex_and_test(input_str, expected_warnings_num, expected_errors_num):
        def mock_get_deposit_withdrawal(url, data, **kwargs):  # pylint: disable=unused-argument
            return MockResponse(200, input_str)
        with patch.object(sandbox_bitmex.session, 'get', side_effect=mock_get_deposit_withdrawal):
            movements = sandbox_bitmex.query_online_deposits_withdrawals(
                start_ts=0,
                end_ts=now,
            )

        if expected_warnings_num == 0 and expected_errors_num == 0:
            assert len(movements) == 1
        else:
            assert len(movements) == 0
            errors = sandbox_bitmex.msg_aggregator.consume_errors()
            warnings = sandbox_bitmex.msg_aggregator.consume_warnings()
            assert len(errors) == expected_errors_num
            assert len(warnings) == expected_warnings_num

    # First try with correct data to make sure everything works
    query_bitmex_and_test(original_input, expected_warnings_num=0, expected_errors_num=0)

    # From here and on present unexpected data
    # invalid timestamp
    given_input = original_input.replace('"2018-09-15T12:30:56.475Z"', '"dasd"')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid asset
    given_input = original_input.replace('"XBt"', '[]')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)

    # unknown asset
    given_input = original_input.replace('"XBt"', '"dadsdsa"')
    query_bitmex_and_test(given_input, expected_warnings_num=1, expected_errors_num=0)

    # invalid amount
    given_input = original_input.replace('16960386', 'null')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)

    # make sure that fee null/none works
    given_input = original_input.replace('800', 'null')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=0)

    # invalid fee
    given_input = original_input.replace('800', '"dadsdsa"')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)

    # missing key error
    given_input = original_input.replace('"amount": 16960386,', '')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)

    # check that if 'transactType` key is missing things still work
    given_input = original_input.replace('"transactType": "Withdrawal",', '')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)


def test_bitmex_margin_history(sandbox_bitmex):
    result = sandbox_bitmex.query_margin_history(
        start_ts=1536492800,
        end_ts=1536492976,
    )
    assert len(result) == 0

    until_9_results_ts = 1536615593
    result = sandbox_bitmex.query_margin_history(
        start_ts=0,
        end_ts=until_9_results_ts,
    )
    resulting_margin_positions = [
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.00000003'),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='97402f76-828e-a8ea-5d26-920134924149',
            notes='XBTZ18',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.0000004'),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='c74e6967-1411-0ad1-e3e3-6f97a04d7202',
            notes='XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.00000183'),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='9c50e247-9bea-b10b-93c8-26845f202e9a',
            notes='XBTJPY',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.00000683'),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='9ab9f275-9132-64aa-4aa6-8c6503418ac6',
            notes='ETHUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000002'),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='7366644c-15ba-baa4-b300-615b0c5db567',
            notes='XRPU18',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000003'),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='0227cf99-09d4-b6f0-86c3-69711cf8da1b',
            notes='XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000003'),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='fa0f5415-0867-6164-e366-d1c73c5558bd',
            notes='XBTJPY',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000005'),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='05c8bbc0-9b03-ff55-60b9-4f22fd2eeab2',
            notes='ETHUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('-0.00007992'),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='df46338a-da5e-e16c-9753-3e863d83d92c',
            notes='ETHU18',
        ),
    ]
    assert result == resulting_margin_positions


def test_bitmex_query_balances(sandbox_bitmex):
    mock_response = {'amount': 123456789}
    with patch.object(sandbox_bitmex, '_api_query_dict', return_value=mock_response):
        balances, msg = sandbox_bitmex.query_balances()

    assert msg == ''
    assert len(balances) == 1
    assert balances[A_BTC].amount == FVal('1.23456789')
    assert balances[A_BTC].usd_value == FVal('1.851851835')

    warnings = sandbox_bitmex.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
