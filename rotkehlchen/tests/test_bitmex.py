import pytest
from rotkehlchen.bitmex import Bitmex
from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import AssetMovement
from rotkehlchen.utils import ts_now

TEST_BITMEX_API_KEY = b'XY98JYVL15Zn-iU9f7OsJeVf'
TEST_BITMEX_API_SECRET = b'671tM6f64bt6KhteDakj2uCCNBt7HhZVEE7H5x16Oy4zb1ag'


@pytest.fixture
def mock_bitmex(accounting_data_dir, inquirer):
    # API key/secret from tests cases here: https://www.bitmex.com/app/apiKeysUsage
    bitmex = Bitmex(
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
            category='Withdrawal',
            timestamp=1536486785,
            asset='BTC',
            amount=FVal('0.00700000'),
            fee=FVal('0.00300000')
        ),
        AssetMovement(
            exchange='bitmex',
            category='Deposit',
            timestamp=1536486277,
            asset='BTC',
            amount=FVal(0.46966992),
            fee=FVal(0)
        ),
    ]
    assert result == expected_result
