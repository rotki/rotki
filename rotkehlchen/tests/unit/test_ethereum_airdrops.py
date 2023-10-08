from unittest.mock import Mock, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.airdrops import AIRDROPS, POAP_AIRDROPS, check_airdrops
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_1INCH, A_GRAIN, A_UNI
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import UnableToDecryptRemoteData
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS

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
def test_check_airdrops(ethereum_accounts, database):
    # create airdrop claim events to test the claimed attribute
    tolerance_for_amount_check = FVal('0.1')
    claim_events = [
        EvmEvent(
            tx_hash=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(1594500575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_UNI,
            balance=Balance(amount=FVal('400') + tolerance_for_amount_check * FVal('0.25')),  # inside tolerance  # noqa: E501
            location_label=string_to_evm_address(TEST_ADDR1),
        ), EvmEvent(
            tx_hash=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(1594500575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_1INCH,
            balance=Balance(amount=FVal('630.374421472277638654') + tolerance_for_amount_check * FVal('2')),  # outside tolerance  # noqa: E501
            location_label=string_to_evm_address(TEST_ADDR1),
        ),
    ]

    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(write_cursor, claim_events)

    def mock_requests_get(url: str, timeout: int):  # pylint: disable=unused-argument
        """Mocking the airdrop data is very convenient here because the airdrop data is quite large
        and read timeout errors can happen even with 90secs threshold. Vcr-ing it is not possible
        because the vcr yaml file is above the github limit of 100MB."""
        url_to_data_map = {
            AIRDROPS['uniswap'][0]:
                f'address,uni,is_lp,is_user,is_socks\n{TEST_ADDR1},400,False,True,False\n{TEST_ADDR2},400.050642,True,True,False\n',
            AIRDROPS['1inch'][0]:
                f'address,tokens\n{TEST_ADDR1},630.374421472277638654\n',
            AIRDROPS['shapeshift'][0]:
                f'address,tokens\n{TEST_ADDR1},200\n',
            AIRDROPS['cow_gnosis'][0]:
                f'address,tokens\n{TEST_ADDR1},99807039723201809834\n',
            AIRDROPS['diva'][0]:
                f'address,tokens\n{TEST_ADDR1},84000\n',
            AIRDROPS['grain'][0]:
                f'address,tokens\n{TEST_ADDR2},16301717650649890035791\n',
        }
        mock_response = Mock()
        mock_response.text = url_to_data_map.get(url, 'address,tokens\n')  # Return the data from the dictionary or just a header if 'url' is not found  # noqa: E501
        if url in [poap_url[0] for poap_url in POAP_AIRDROPS.values()]:
            mock_response.text = '{}'  # any valid json response will do because tested addresses do not have poap airdrops  # noqa: E501
        mock_response.content = mock_response.text.encode('utf-8')
        return mock_response

    with (
        patch('rotkehlchen.chain.ethereum.airdrops.SMALLEST_AIRDROP_SIZE', 1),
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=mock_requests_get),
    ):
        data = check_airdrops(
            addresses=ethereum_accounts + [TEST_ADDR1, TEST_ADDR2],
            database=database,
            tolerance_for_amount_check=tolerance_for_amount_check,
        )

    # Test data is returned for the address correctly
    assert len(data) == 2
    assert len(data[TEST_ADDR1]) == 5
    assert data[TEST_ADDR1]['uniswap'] == {
        'amount': '400',
        'asset': A_UNI,
        'link': 'https://app.uniswap.org/',
        'claimed': True,
    }
    assert data[TEST_ADDR1]['1inch'] == {
        'amount': '630.374421472277638654',
        'asset': A_1INCH,
        'link': 'https://1inch.exchange/',
        'claimed': False,
    }

    assert len(data[TEST_ADDR2]) == 2
    assert data[TEST_ADDR2]['uniswap'] == {
        'amount': '400.050642',
        'asset': A_UNI,
        'link': 'https://app.uniswap.org/',
        'claimed': False,
    }
    assert data[TEST_ADDR2]['grain'] == {
        'amount': '16301.717650649890035791',
        'asset': A_GRAIN,
        'link': 'https://claim.harvest.finance/',
        'claimed': False,
    }

    # Test cache files are created
    for protocol_name in AIRDROPS:
        assert (database.user_data_dir.parent / 'airdrops' / f'{protocol_name}.csv').is_file()


@pytest.mark.parametrize('airdrop_list', [NOT_CSV_WEBPAGE])
def test_airdrop_fail(mock_airdrop_list, database):  # pylint: disable=unused-argument
    with pytest.raises(UnableToDecryptRemoteData):
        check_airdrops(
            addresses=[TEST_ADDR1],
            database=database,
        )
