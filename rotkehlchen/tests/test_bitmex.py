from unittest.mock import patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.exchanges.data_structures import AssetMovement, Exchange, MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.utils.misc import ts_now


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


def test_bitmex_api_withdrawals_deposit(test_bitmex):
    """Test the happy case of bitmex withdrawals deposit query"""
    result = test_bitmex.query_deposits_withdrawals(
        start_ts=1536492800,
        end_ts=1536492976,
        end_at_least_ts=1536492976,
    )
    assert len(result) == 0

    now = ts_now()
    result = test_bitmex.query_deposits_withdrawals(
        start_ts=0,
        end_ts=now,
        end_at_least_ts=now,
    )
    expected_result = [
        AssetMovement(
            exchange=Exchange.BITMEX,
            category='deposit',
            timestamp=1537014656,
            asset='BTC',
            amount=FVal(0.16960386),
            fee=FVal(0E-8),
        ),
        AssetMovement(
            exchange=Exchange.BITMEX,
            category='deposit',
            timestamp=1536563759,
            asset='BTC',
            amount=FVal('0.38474377'),
            fee=FVal(0),
        ),
        AssetMovement(
            exchange=Exchange.BITMEX,
            category='withdrawal',
            timestamp=1536536707,
            asset='BTC',
            amount=FVal('0.00700000'),
            fee=FVal('0.00300000'),
        ),
        AssetMovement(
            exchange=Exchange.BITMEX,
            category='deposit',
            timestamp=1536486278,
            asset='BTC',
            amount=FVal('0.46966992'),
            fee=FVal(0),
        ),

    ]
    assert result == expected_result
    # also make sure that asset movements contain Asset and not strings
    for movement in result:
        assert isinstance(movement.asset, Asset)


def test_bitmex_api_withdrawals_deposit_unexpected_data(test_bitmex):
    """Test getting unexpected data in bitmex withdrawals deposit query is handled gracefully"""
    test_bitmex.cache_ttl_secs = 0

    original_input = """[{
"transactID": "b6c6fd2c-4d0c-b101-a41c-fa5aa1ce7ef1", "account": 126541, "currency": "XBt",
 "transactType": "Withdrawal", "amount": 16960386, "fee": 800, "transactStatus": "Completed",
 "address": "", "tx": "", "text": "", "transactTime": "2018-09-15T12:30:56.475Z",
 "walletBalance": 103394923, "marginBalance": null,
 "timestamp": "2018-09-15T12:30:56.475Z"}]"""
    now = ts_now()

    def query_bitmex_and_test(input_str, expected_warnings_num, expected_errors_num):
        def mock_get_deposit_withdrawal(url, data):  # pylint: disable=unused-argument
            return MockResponse(200, input_str)
        with patch.object(test_bitmex.session, 'get', side_effect=mock_get_deposit_withdrawal):
            movements = test_bitmex.query_deposits_withdrawals(
                start_ts=0,
                end_ts=now,
                end_at_least_ts=now,
            )

        if expected_warnings_num == 0 and expected_errors_num == 0:
            assert len(movements) == 1
        else:
            assert len(movements) == 0
            errors = test_bitmex.msg_aggregator.consume_errors()
            warnings = test_bitmex.msg_aggregator.consume_warnings()
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


def test_bitmex_trade_history(test_bitmex):
    result = test_bitmex.query_trade_history(
        start_ts=1536492800,
        end_ts=1536492976,
        end_at_least_ts=1536492976,
    )
    assert len(result) == 0

    until_9_results_ts = 1536615593
    result = test_bitmex.query_trade_history(
        start_ts=0,
        end_ts=until_9_results_ts,
        end_at_least_ts=until_9_results_ts,
    )
    resulting_margin_positions = [
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.00000003'),
            pl_currency=A_BTC,
            notes='XBTZ18',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.0000004'),
            pl_currency=A_BTC,
            notes='XBTUSD',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.00000183'),
            pl_currency=A_BTC,
            notes='XBTJPY',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.00000683'),
            pl_currency=A_BTC,
            notes='ETHUSD',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000002'),
            pl_currency=A_BTC,
            notes='XRPU18',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000003'),
            pl_currency=A_BTC,
            notes='XBTUSD',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000003'),
            pl_currency=A_BTC,
            notes='XBTJPY',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000005'),
            pl_currency=A_BTC,
            notes='ETHUSD',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('-0.00007992'),
            pl_currency=A_BTC,
            notes='ETHU18',
        ),
    ]
    assert result == resulting_margin_positions
