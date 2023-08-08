from unittest.mock import patch

import pytest

from rotkehlchen.chain.ethereum.airdrops import AIRDROPS, check_airdrops
from rotkehlchen.constants.assets import A_1INCH, A_GRAIN, A_UNI
from rotkehlchen.errors.misc import UnableToDecryptRemoteData

TEST_ADDR1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
TEST_ADDR2 = '0x51985CE8BB9AB1708746b24e22e37CD7A980Ec24'
NOT_CSV_WEBPAGE = {
    'test': (
        'https://github.com/rotki/yabirgb',
        A_UNI,
        'https://github.com',
    ),
}


@pytest.fixture(name='mock_airdrop_list')
def _fixture_airdrop_list(airdrop_list):
    with patch(
        'rotkehlchen.chain.ethereum.airdrops.AIRDROPS',
        new=airdrop_list,
    ):
        yield


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_check_airdrops(ethereum_accounts, data_dir):
    data = check_airdrops(
        addresses=ethereum_accounts + [TEST_ADDR1, TEST_ADDR2],
        data_dir=data_dir,
    )

    # Test data is returned for the address correctly
    assert len(data) == 2
    assert len(data[TEST_ADDR1]) == 5
    assert data[TEST_ADDR1]['uniswap'] == {
        'amount': '400',
        'asset': A_UNI,
        'link': 'https://app.uniswap.org/',
    }
    assert data[TEST_ADDR1]['1inch'] == {
        'amount': '630.374421472277638654',
        'asset': A_1INCH,
        'link': 'https://1inch.exchange/',
    }

    assert len(data[TEST_ADDR2]) == 2
    assert data[TEST_ADDR2]['uniswap'] == {
        'amount': '400.050642',
        'asset': A_UNI,
        'link': 'https://app.uniswap.org/',
    }
    assert data[TEST_ADDR2]['grain'] == {
        'amount': '16301.717650649890035791',
        'asset': A_GRAIN,
        'link': 'https://claim.harvest.finance/',
    }

    # Test cache files are created
    for protocol_name in AIRDROPS:
        assert (data_dir / 'airdrops' / f'{protocol_name}.csv').is_file()


@pytest.mark.parametrize('airdrop_list', [NOT_CSV_WEBPAGE])
def test_airdrop_fail(data_dir, mock_airdrop_list):  # pylint: disable=unused-argument
    with pytest.raises(UnableToDecryptRemoteData):
        check_airdrops(
            addresses=[TEST_ADDR1],
            data_dir=data_dir,
        )
