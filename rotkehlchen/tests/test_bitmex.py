import pytest
from rotkehlchen.bitmex import Bitmex, trade_from_bitmex
from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import AssetMovement, MarginPosition
from rotkehlchen.utils import ts_now

TEST_BITMEX_API_KEY = b'XY98JYVL15Zn-iU9f7OsJeVf'
TEST_BITMEX_API_SECRET = b'671tM6f64bt6KhteDakj2uCCNBt7HhZVEE7H5x16Oy4zb1ag'


@pytest.fixture
def mock_bitmex(accounting_data_dir, inquirer):
    # API key/secret from tests cases here: https://www.bitmex.com/app/apiKeysUsage
    bitmex = Bitmex(
        0,
        b'LAqUlngMIQkIUjXMUreyu3qn',
        b'chNOOS4KvNXR_Xq4k4c9qsfoKWvnDecLATCRlcBwyKDYnWgO',
        inquirer,
        accounting_data_dir,
    )

    bitmex.first_connection_made = True
    return bitmex


@pytest.fixture
def test_bitmex(accounting_data_dir, inquirer):
    # API key/secret from tests cases here: https://www.bitmex.com/app/apiKeysUsage
    bitmex = Bitmex(
        0,
        TEST_BITMEX_API_KEY,
        TEST_BITMEX_API_SECRET,
        inquirer,
        accounting_data_dir,
    )
    bitmex.uri = 'https://testnet.bitmex.com'
    return bitmex


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
            exchange='bitmex',
            category='Deposit',
            timestamp=1537014656,
            asset='BTC',
            amount=FVal(0.16960386),
            fee=FVal(0E-8),
        ),
        AssetMovement(
            exchange='bitmex',
            category='Deposit',
            timestamp=1536563759,
            asset='BTC',
            amount=FVal('0.38474377'),
            fee=FVal(0),
        ),
        AssetMovement(
            exchange='bitmex',
            category='Withdrawal',
            timestamp=1536536706,
            asset='BTC',
            amount=FVal('0.00700000'),
            fee=FVal('0.00300000'),
        ),
        AssetMovement(
            exchange='bitmex',
            category='Deposit',
            timestamp=1536486277,
            asset='BTC',
            amount=FVal('0.46966992'),
            fee=FVal(0),
        ),

    ]
    assert result == expected_result


BITMEX_FIRST_9_TRADES = [
    {
        'transactID': '97402f76-828e-a8ea-5d26-920134924149',
        'account': 126541,
        'currency': 'XBt',
        'transactType': 'RealisedPNL',
        'amount': 3,
        'fee': 0,
        'transactStatus': 'Completed',
        'address': 'XBTZ18',
        'tx': 'fe115e83-7917-49f3-c170-0b23c208c018',
        'text': '',
        'transactTime': '2018-09-10T12:00:00.000Z',
        'walletBalance': 86434299,
        'marginBalance': None,
        'timestamp': '2018-09-10T12:00:00.208Z',
    }, {
        'transactID': 'c74e6967-1411-0ad1-e3e3-6f97a04d7202',
        'account': 126541,
        'currency': 'XBt',
        'transactType': 'RealisedPNL',
        'amount': 40,
        'fee': 0,
        'transactStatus': 'Completed',
        'address': 'XBTUSD',
        'tx': 'fe115e83-7917-49f3-c170-0b23c208c018',
        'text': '',
        'transactTime': '2018-09-10T12:00:00.000Z',
        'walletBalance': 86434296,
        'marginBalance': None,
        'timestamp': '2018-09-10T12:00:00.208Z',
    }, {
        'transactID': '9c50e247-9bea-b10b-93c8-26845f202e9a',
        'account': 126541,
        'currency': 'XBt',
        'transactType': 'RealisedPNL',
        'amount': 183,
        'fee': 0,
        'transactStatus': 'Completed',
        'address': 'XBTJPY',
        'tx': 'fe115e83-7917-49f3-c170-0b23c208c018',
        'text': '',
        'transactTime': '2018-09-10T12:00:00.000Z',
        'walletBalance': 86434256,
        'marginBalance': None,
        'timestamp': '2018-09-10T12:00:00.208Z',
    }, {
        'transactID': '9ab9f275-9132-64aa-4aa6-8c6503418ac6',
        'account': 126541,
        'currency': 'XBt',
        'transactType': 'RealisedPNL',
        'amount': 683,
        'fee': 0,
        'transactStatus': 'Completed',
        'address': 'ETHUSD',
        'tx': 'fe115e83-7917-49f3-c170-0b23c208c018',
        'text': '',
        'transactTime': '2018-09-10T12:00:00.000Z',
        'walletBalance': 86434073,
        'marginBalance': None,
        'timestamp': '2018-09-10T12:00:00.208Z',
    }, {
        'transactID': '7366644c-15ba-baa4-b300-615b0c5db567',
        'account': 126541,
        'currency': 'XBt',
        'transactType': 'RealisedPNL',
        'amount': 2,
        'fee': 0,
        'transactStatus': 'Completed',
        'address': 'XRPU18',
        'tx': '4c13d7fc-5bf6-85d8-bce3-2d2d69d69951',
        'text': '',
        'transactTime': '2018-09-09T12:00:00.000Z',
        'walletBalance': 47959013,
        'marginBalance': None,
        'timestamp': '2018-09-09T12:00:00.222Z',
    }, {
        'transactID': '0227cf99-09d4-b6f0-86c3-69711cf8da1b',
        'account': 126541,
        'currency': 'XBt',
        'transactType': 'RealisedPNL',
        'amount': 3,
        'fee': 0,
        'transactStatus': 'Completed',
        'address': 'XBTUSD',
        'tx': '4c13d7fc-5bf6-85d8-bce3-2d2d69d69951',
        'text': '',
        'transactTime': '2018-09-09T12:00:00.000Z',
        'walletBalance': 47959011,
        'marginBalance': None,
        'timestamp': '2018-09-09T12:00:00.222Z',
    }, {
        'transactID': 'fa0f5415-0867-6164-e366-d1c73c5558bd',
        'account': 126541,
        'currency': 'XBt',
        'transactType': 'RealisedPNL',
        'amount': 3,
        'fee': 0,
        'transactStatus': 'Completed',
        'address': 'XBTJPY',
        'tx': '4c13d7fc-5bf6-85d8-bce3-2d2d69d69951',
        'text': '',
        'transactTime': '2018-09-09T12:00:00.000Z',
        'walletBalance': 47959008,
        'marginBalance': None,
        'timestamp': '2018-09-09T12:00:00.222Z',
    }, {
        'transactID': '05c8bbc0-9b03-ff55-60b9-4f22fd2eeab2',
        'account': 126541,
        'currency': 'XBt',
        'transactType': 'RealisedPNL',
        'amount': 5,
        'fee': 0,
        'transactStatus': 'Completed',
        'address': 'ETHUSD',
        'tx': '4c13d7fc-5bf6-85d8-bce3-2d2d69d69951',
        'text': '',
        'transactTime': '2018-09-09T12:00:00.000Z',
        'walletBalance': 47959005,
        'marginBalance': None,
        'timestamp': '2018-09-09T12:00:00.222Z',
    }, {
        'transactID': 'df46338a-da5e-e16c-9753-3e863d83d92c',
        'account': 126541,
        'currency': 'XBt',
        'transactType': 'RealisedPNL',
        'amount': -7992,
        'fee': 0,
        'transactStatus': 'Completed',
        'address': 'ETHU18',
        'tx': '4c13d7fc-5bf6-85d8-bce3-2d2d69d69951',
        'text': '',
        'transactTime': '2018-09-09T12:00:00.000Z',
        'walletBalance': 47959000,
        'marginBalance': None,
        'timestamp': '2018-09-09T12:00:00.222Z',
    }]


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
    assert result == BITMEX_FIRST_9_TRADES


def test_trade_from_bitmex():
    margin_positions = [
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.00000003'),
            pl_currency='BTC',
            notes='XBTZ18',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.0000004'),
            pl_currency='BTC',
            notes='XBTUSD',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.00000183'),
            pl_currency='BTC',
            notes='XBTJPY',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536580800,
            profit_loss=FVal('0.00000683'),
            pl_currency='BTC',
            notes='ETHUSD',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000002'),
            pl_currency='BTC',
            notes='XRPU18',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000003'),
            pl_currency='BTC',
            notes='XBTUSD',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000003'),
            pl_currency='BTC',
            notes='XBTJPY',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('0.00000005'),
            pl_currency='BTC',
            notes='ETHUSD',
        ),
        MarginPosition(
            exchange='bitmex',
            open_time=None,
            close_time=1536494400,
            profit_loss=FVal('-0.00007992'),
            pl_currency='BTC',
            notes='ETHU18',
        ),

    ]

    assert len(BITMEX_FIRST_9_TRADES) == len(margin_positions)
    for idx, trade in enumerate(BITMEX_FIRST_9_TRADES):
        position = trade_from_bitmex(trade)
        assert position == margin_positions[idx]
