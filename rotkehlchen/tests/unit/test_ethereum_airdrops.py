import pytest
from rotkehlchen.chain.ethereum.airdrops import check_airdrops, AIRDROPS
from rotkehlchen.constants.assets import A_UNI, A_1INCH

TEST_ADDR = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_check_airdrops(ethereum_accounts, data_dir):
    data = check_airdrops(
        addresses=ethereum_accounts + [TEST_ADDR],
        data_dir=data_dir,
    )

    # Test data is returned for the address correctly
    assert len(data) == 1
    assert len(data[TEST_ADDR]) == 2
    assert data[TEST_ADDR]['uniswap'] == {
        'amount': '400',
        'asset': A_UNI,
        'link': 'https://app.uniswap.org/',
    }
    assert data[TEST_ADDR]['1inch'] == {
        'amount': '630.374421472277638654',
        'asset': A_1INCH,
        'link': 'https://1inch.exchange/',
    }

    # Test cache files are created
    for protocol_name in AIRDROPS:
        assert (data_dir / 'airdrops' / f'{protocol_name}.csv').is_file()
