import datetime
from unittest.mock import Mock, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.airdrops import AIRDROPS_INDEX, AIRDROPS_REPO_BASE, check_airdrops
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_1INCH, A_GRAIN, A_SHU, A_UNI
from rotkehlchen.constants.misc import AIRDROPSDIR_NAME, AIRDROPSPOAPDIR_NAME, APPDIR_NAME
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_get_unique_cache_value
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import CacheType, Location, TimestampMS
from rotkehlchen.utils.serialization import rlk_jsondumps

TEST_ADDR1 = string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12')
TEST_ADDR2 = string_to_evm_address('0x51985CE8BB9AB1708746b24e22e37CD7A980Ec24')
TEST_POAP1 = string_to_evm_address('0x043e2a6047e50710e0f5189DBA7623C4A183F871')
NOT_CSV_WEBPAGE = {
    'airdrops': {
        'test': {
            'csv_path': 'notavalidpath/yabirgb',
            'asset_identifier': 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
            'url': 'https://github.com',
            'name': 'Yabirgb',
            'icon': 'yabirgb.png',
        },
    }, 'poap_airdrops': {},
}
MOCK_AIRDROP_INDEX = {'airdrops': {
    'uniswap': {
        'csv_path': 'airdrops/uniswap.csv',
        'asset_identifier': 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
        'url': 'https://app.uniswap.org/',
        'name': 'Uniswap',
        'icon': 'uniswap.svg',
    },
    '1inch': {
        'csv_path': 'airdrops/1inch.csv',
        'asset_identifier': 'eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302',
        'url': 'https://1inch.exchange/',
        'name': '1inch',
        'icon': '1inch.svg',
    },
    'grain': {
        'csv_path': 'airdrops/grain_iou.csv',
        'asset_identifier': 'eip155:1/erc20:0x6589fe1271A0F29346796C6bAf0cdF619e25e58e',
        'url': 'https://claim.harvest.finance/',
        'name': 'Grain',
        'icon': 'grain.png',
        'icon_path': 'airdrops/icons/grain.svg',
    },
    'shapeshift': {
        'csv_path': 'airdrops/shapeshift.csv',
        'asset_identifier': 'eip155:1/erc20:0xc770EEfAd204B5180dF6a14Ee197D99d808ee52d',
        'url': 'https://shapeshift.com/shapeshift-decentralize-airdrop',
        'name': 'ShapeShift',
        'icon': 'shapeshift.svg',
    },
    'cow_gnosis': {
        'csv_path': 'airdrops/cow_gnosis.csv',
        'asset_identifier': 'eip155:100/erc20:0xc20C9C13E853fc64d054b73fF21d3636B2d97eaB',
        'url': 'https://cowswap.exchange/#/claim',
        'name': 'COW (gnosis chain)',
        'icon': 'cow.svg',
    },
    'diva': {
        'csv_path': 'airdrops/diva.csv',
        'asset_identifier': 'eip155:1/erc20:0xBFAbdE619ed5C4311811cF422562709710DB587d',
        'url': 'https://claim.diva.community/',
        'name': 'DIVA',
        'icon': 'diva.svg',
    },
    'shutter': {
        'csv_path': 'airdrops/shutter.csv',
        'asset_identifier': 'eip155:1/erc20:0xe485E2f1bab389C08721B291f6b59780feC83Fd7',
        'url': 'https://claim.shutter.network/',
        'name': 'SHU',
        'icon': 'shutter.png',
        'cutoff_time': 1721000000,
    },
}, 'poap_airdrops': {
    'aave_v2_pioneers': [
        'airdrops/poap/poap_aave_v2_pioneers.json',
        'https://poap.delivery/aave-v2-pioneers',
        'AAVE V2 Pioneers',
    ],
}}


def _mock_airdrop_list(url: str, timeout: int = 0):  # pylint: disable=unused-argument
    mock_response = Mock()
    if url == AIRDROPS_INDEX:
        mock_response.json = lambda: NOT_CSV_WEBPAGE
        return mock_response
    else:  # when CSV is queried, return invalid payload
        mock_response.text = mock_response.content = '<>invalid CSV<>'
        return mock_response


@pytest.mark.freeze_time()
@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('new_asset_data', [{
    'asset_type': 'EVM_TOKEN',  # test with EVM token
    'address': '0xe485E2f1bab389C08721B291f6b59780feC83Fd7',
    'name': 'Shutter',
    'symbol': 'SHU',
    'chain_id': 1,
    'decimals': 18,
}, {
    'asset_type': 'SOLANA_TOKEN',  # test with non EVM token
    'name': 'Some Non EVM Token',
    'symbol': 'NONEVM',
}])
@pytest.mark.parametrize('remove_global_assets', [['eip155:1/erc20:0xe485E2f1bab389C08721B291f6b59780feC83Fd7']])  # noqa: E501
def test_check_airdrops(freezer, ethereum_accounts, database, new_asset_data, data_dir):
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
    MOCK_AIRDROP_INDEX['airdrops']['shutter']['new_asset_data'] = new_asset_data

    new_asset_identifier = MOCK_AIRDROP_INDEX['airdrops']['shutter']['asset_identifier']
    AssetResolver.assets_cache.clear()  # remove new asset from cache

    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(write_cursor, claim_events)

    def mock_requests_get(url: str, timeout: int = 0):  # pylint: disable=unused-argument
        """Mocking the airdrop data is very convenient here because the airdrop data is quite large
        and read timeout errors can happen even with 90secs threshold. Vcr-ing it is not possible
        because the vcr yaml file is above the github limit of 100MB. The schema of AIRDROPS_INDEX
        is checked in the rotki/data repo."""
        url_to_data_map = {
            AIRDROPS_INDEX: MOCK_AIRDROP_INDEX,
            f'{AIRDROPS_REPO_BASE}/airdrops/uniswap.csv':
                f'address,uni,is_lp,is_user,is_socks\n{TEST_ADDR1},400,False,True,False\n{TEST_ADDR2},400.050642,True,True,False\n',
            f'{AIRDROPS_REPO_BASE}/airdrops/1inch.csv':
                f'address,tokens\n{TEST_ADDR1},630.374421472277638654\n',
            f'{AIRDROPS_REPO_BASE}/airdrops/shapeshift.csv':
                f'address,tokens\n{TEST_ADDR1},200\n',
            f'{AIRDROPS_REPO_BASE}/airdrops/cow_gnosis.csv':
                f'address,tokens\n{TEST_ADDR1},99807039723201809834\n',
            f'{AIRDROPS_REPO_BASE}/airdrops/diva.csv':
                f'address,tokens\n{TEST_ADDR1},84000\n',
            f'{AIRDROPS_REPO_BASE}/airdrops/grain_iou.csv':
                f'address,tokens\n{TEST_ADDR2},16301717650649890035791\n',
            f'{AIRDROPS_REPO_BASE}/airdrops/shutter.csv':
                f'address,tokens\n{TEST_ADDR2},394857.029384576349787465\n',
            f'{AIRDROPS_REPO_BASE}/airdrops/poap/poap_aave_v2_pioneers.json':
                f'{{"{TEST_POAP1}": [\n566\n]}}',
        }
        mock_response = Mock()
        if url == AIRDROPS_INDEX:
            mock_response.json = lambda: url_to_data_map[AIRDROPS_INDEX]
        else:
            mock_response.text = url_to_data_map.get(url, 'address,tokens\n')  # Return the data from the dictionary or just a header if 'url' is not found  # noqa: E501
            assert isinstance(mock_response.text, str)
            mock_response.content = mock_response.text.encode('utf-8')
        return mock_response

    # testing just on the cutoff time of shutter
    freezer.move_to(datetime.datetime.fromtimestamp(1721000000, tz=datetime.UTC))
    with (
        patch('rotkehlchen.chain.ethereum.airdrops.SMALLEST_AIRDROP_SIZE', 1),
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=mock_requests_get),
        patch('rotkehlchen.globaldb.handler.GlobalDBHandler.packaged_db_conn', side_effect=lambda: GlobalDBHandler().conn),  # not using packaged DB to ensure that new tokens are created  # noqa: E501
    ):
        with GlobalDBHandler().conn.read_ctx() as cursor:
            assert cursor.execute(
                'SELECT COUNT(*) FROM assets WHERE identifier=?',
                (new_asset_identifier,),
            ).fetchone()[0] == 0  # asset not present before
        data = check_airdrops(
            addresses=ethereum_accounts + [TEST_ADDR1, TEST_ADDR2, TEST_POAP1],
            database=database,
            data_dir=data_dir,
            tolerance_for_amount_check=tolerance_for_amount_check,
        )
        with GlobalDBHandler().conn.read_ctx() as cursor:
            assert cursor.execute(
                'SELECT COUNT(*) FROM assets WHERE identifier=?',
                (new_asset_identifier,),
            ).fetchone()[0] == 1  # asset present after

    # Test data is returned for the address correctly
    assert len(data) == 3
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

    assert len(data[TEST_ADDR2]) == 3
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
        'icon_url': f'{AIRDROPS_REPO_BASE}/airdrops/icons/grain.svg',
    }
    assert data[TEST_ADDR2]['shutter'] == {
        'amount': '394857.029384576349787465',
        'asset': A_SHU,
        'link': 'https://claim.shutter.network/',
        'claimed': False,
    }
    assert len(data[TEST_POAP1]) == 1
    assert data[TEST_POAP1]['poap'] == [{
        'event': 'aave_v2_pioneers',
        'assets': [566],
        'link': 'https://poap.delivery/aave-v2-pioneers',
        'name': 'AAVE V2 Pioneers',
    }]

    # after cutoff time of shutter
    freezer.move_to(datetime.datetime.fromtimestamp(1721000001, tz=datetime.UTC))
    with (
        patch('rotkehlchen.chain.ethereum.airdrops.SMALLEST_AIRDROP_SIZE', 1),
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get') as mock_get,
    ):
        data = check_airdrops(
            addresses=[TEST_ADDR2],
            database=database,
            data_dir=data_dir,
            tolerance_for_amount_check=tolerance_for_amount_check,
        )
        assert mock_get.call_count == 0  # not queried again because it was cached a second ago
    assert len(data[TEST_ADDR2]) == 2
    assert 'shutter' not in data[TEST_ADDR2]

    freezer.move_to(datetime.datetime.fromtimestamp(1721000001 + 12 * HOUR_IN_SECONDS, tz=datetime.UTC))  # noqa: E501
    with (
        patch('rotkehlchen.chain.ethereum.airdrops.SMALLEST_AIRDROP_SIZE', 1),
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=mock_requests_get) as mock_get,  # noqa: E501
    ):
        data = check_airdrops(
            addresses=[TEST_ADDR2],
            database=database,
            data_dir=data_dir,
            tolerance_for_amount_check=tolerance_for_amount_check,
        )
        assert mock_get.call_count == 1  # queried again because it was cached 12 hours ago

    # Test cache file and row is created
    for protocol_name in MOCK_AIRDROP_INDEX['airdrops']:
        assert (data_dir / APPDIR_NAME / AIRDROPSDIR_NAME / f'{protocol_name}.csv').is_file()
    for protocol_name in MOCK_AIRDROP_INDEX['poap_airdrops']:
        assert (data_dir / APPDIR_NAME / AIRDROPSPOAPDIR_NAME / f'{protocol_name}.json').is_file()
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.AIRDROPS_METADATA,),
        ) == rlk_jsondumps(MOCK_AIRDROP_INDEX)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_airdrop_fail(database, data_dir):
    with (
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=_mock_airdrop_list),
        pytest.raises(RemoteError),
    ):
        check_airdrops(
            addresses=[TEST_ADDR1],
            database=database,
            data_dir=data_dir,
        )
