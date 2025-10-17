import datetime
import json
from collections import defaultdict
from copy import deepcopy
from http import HTTPStatus
from io import BytesIO, StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import polars as pl
import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.airdrops import (
    AIRDROP_IDENTIFIER_KEY,
    AIRDROPS_INDEX,
    AIRDROPS_REPO_BASE,
    ETAG_CACHE_KEY,
    _parse_airdrops,
    check_airdrops,
    check_linea_airdrop,
    fetch_airdrops_metadata,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_1INCH, A_SHU, A_UNI
from rotkehlchen.constants.misc import AIRDROPSDIR_NAME, AIRDROPSPOAPDIR_NAME, APPDIR_NAME
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import CacheType, Location, TimestampMS
from rotkehlchen.utils.serialization import rlk_jsondumps

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

TEST_ADDR1 = string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12')
TEST_ADDR2 = string_to_evm_address('0x51985CE8BB9AB1708746b24e22e37CD7A980Ec24')
TEST_POAP1 = string_to_evm_address('0x043e2a6047e50710e0f5189DBA7623C4A183F871')
NOT_CSV_WEBPAGE = {
    'airdrops': {
        'test': {
            'file_path': 'notavalidpath/yabirgb',
            'file_hash': 'd39fdc7913b4cbafc90cd0458c9e88656e951d9c216a9f4c0e973b7e7c6f1882',
            'asset_identifier': 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
            'url': 'https://github.com',
            'name': 'Yabirgb',
            'icon': 'yabirgb.png',
        },
    }, 'poap_airdrops': {},
}
MOCK_AIRDROP_INDEX = {'airdrops': {
    'uniswap': {
        'file_path': 'airdrops/uniswap.parquet',
        'file_hash': '87c81b0070d4a19ab87fd631b79247293031412706ec5414a859899572470ddf',
        'asset_identifier': 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
        'url': 'https://app.uniswap.org/',
        'name': 'Uniswap',
        'icon': 'uniswap.svg',
    },
    '1inch': {
        'file_path': 'airdrops/1inch.parquet',
        'file_hash': '7f8a67b1fe7c2019bcac956777d306dd372ebe5bc2a9cd920129884170562108',
        'asset_identifier': 'eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302',
        'url': 'https://1inch.exchange/',
        'name': '1inch',
        'icon': '1inch.svg',
    },
    'grain': {
        'file_path': 'airdrops/grain_iou.parquet',
        'file_hash': 'dff6b525931ac7ad321efd8efc419370a9d7a222e92b1aad7a985b7e61248121',
        'asset_identifier': 'eip155:1/erc20:0x6589fe1271A0F29346796C6bAf0cdF619e25e58e',
        'url': 'https://claim.harvest.finance/',
        'name': 'Grain',
        'icon': 'grain.png',
        'icon_path': 'airdrops/icons/grain.svg',
    },
    'shapeshift': {
        'file_path': 'airdrops/shapeshift.parquet',
        'file_hash': '97b599c62af4391a19c17b47bd020733801e28a443443ad7e1602c647c9ebfe2',
        'asset_identifier': 'eip155:1/erc20:0xc770EEfAd204B5180dF6a14Ee197D99d808ee52d',
        'url': 'https://shapeshift.com/shapeshift-decentralize-airdrop',
        'name': 'ShapeShift',
        'icon': 'shapeshift.svg',
    },
    'cow_gnosis': {
        'file_path': 'airdrops/cow_gnosis.parquet',
        'file_hash': 'f7fea2a5806c67a27c15bb4e05c3fd6c0c1ab51f5bd2a23c29852fa2f95a7db3',
        'asset_identifier': 'eip155:100/erc20:0xc20C9C13E853fc64d054b73fF21d3636B2d97eaB',
        'url': 'https://cowswap.exchange/#/claim',
        'name': 'COW (gnosis chain)',
        'icon': 'cow.svg',
    },
    'diva': {
        'file_path': 'airdrops/diva.parquet',
        'file_hash': '50cf9f2bb2f769ae20dc699809b8bdca5f48ce695c792223ad93f8681ab8d0fc',
        'asset_identifier': 'eip155:1/erc20:0xBFAbdE619ed5C4311811cF422562709710DB587d',
        'url': 'https://claim.diva.community/',
        'name': 'DIVA',
        'icon': 'diva.svg',
    },
    'shutter': {
        'file_path': 'airdrops/shutter.parquet',
        'file_hash': 'd4427f41181803df49901241ec89ed6a235b8b67cc4ef5cfdef1515dc84704d1',
        'asset_identifier': 'eip155:1/erc20:0xe485E2f1bab389C08721B291f6b59780feC83Fd7',
        'url': 'https://claim.shutter.network/',
        'name': 'SHU',
        'icon': 'shutter.png',
        'cutoff_time': 1721000000,
    },
    'invalid': {
        'file_path': 'airdrops/invalid.parquet',
        'file_hash': 'a426abd9f7af3ec3138fe393e4735129a5884786b7bbda8de30002c134951aec',
        'asset_identifier': 'eip155:1/erc20:0xe485E2f1bab389C08721B291f6b59780feC83Fd7',
        'url': 'https://claim.invalid.community/',
        'name': 'INVALID',
        'icon': 'invalid.svg',
    },
    'degen2_season1': {
        'file_path': 'airdrops/degen2_season1.parquet',
        'file_hash': '708ae1fcbe33a11a91fd05e1e7c4fa2d514b65cb1f8d3e4ce3556e7bdd8af2f5',
        'asset_identifier': 'eip155:8453/erc20:0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed',
        'url': 'https://www.degen.tips/airdrop2/season1',
        'name': 'DEGEN',
        'icon': 'degen.svg',
        'icon_path': 'airdrops/icons/degen.svg',
        'new_asset_data': {
            'asset_type': 'EVM_TOKEN',
            'address': '0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed',
            'name': 'Degen',
            'symbol': 'DEGEN',
            'chain_id': 8453,
            'decimals': 18,
        },
    },
    'degen2_season3': {
        'file_path': 'airdrops/degen2_season3.parquet',
        'file_hash': '7b3ee9fd6bebfe5a640c40ba4effe29ce5f0bd1e05c9222fb25f1859f9af0a6f',
        'asset_identifier': 'eip155:8453/erc20:0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed',
        'url': 'https://www.degen.tips/airdrop2/season3',
        'name': 'DEGEN',
        'icon': 'degen.svg',
        'icon_path': 'airdrops/icons/degen.svg',
        'cutoff_time': 1716940800,
        'new_asset_data': {
            'asset_type': 'EVM_TOKEN',
            'address': '0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed',
            'name': 'Degen',
            'symbol': 'DEGEN',
            'chain_id': 8453,
            'decimals': 18,
        },
    },
    'debridge_1': {
        'file_path': 'airdrops/debridge_1.parquet',
        'file_hash': 'aea1b729dea8ae1e2b412c5c6d821854cde4dc84ad996e54ba76439e08fabb58',
        'asset_identifier': 'DBR',
        'url': 'https://debridge.foundation/',
        'name': 'DBR',
        'icon': 'debridge.svg',
        'icon_path': 'airdrops/icons/debridge.svg',
        'new_asset_data': {
            'asset_type': 'SOLANA_TOKEN',
            'name': 'DeBridge',
            'address': 'DBRiDgJAMsM95moTzJs7M9LnkGErpbv9v6CUR1DXnUu5',
            'symbol': 'DBR',
            'decimals': 6,
            'coingecko': 'debridge',
        },
    },
    'eigen': {
        'asset_identifier': 'EIGEN_TOKEN_PRE_RELEASE',
        'url': 'https://eigenfoundation.org',
        'api_url': 'https://claims.eigenfoundation.org/clique-eigenlayer-api/campaign/eigenlayer/credentials?walletAddress={address}',
        'amount_path': 'data/pipelines/tokenQualified',
        'name': 'EIGEN',
        'icon': 'eigen.svg',
        'icon_path': 'airdrops/icons/eigen.svg',
        'new_asset_data': {
            'asset_type': 'OTHER',
            'name': 'Eigen',
            'symbol': 'EIGEN',  # do not include chainid on purpose to see code handles it properly
        },
    },
}, 'poap_airdrops': {
    'aave_v2_pioneers': [
        'airdrops/poap/poap_aave_v2_pioneers.json',
        'https://poap.delivery/aave-v2-pioneers',
        'AAVE V2 Pioneers',
        '388003b6c0dc589981ce9e962d6d8b6b2148c72ccf6ec3578ab32d63b547f903',
    ],
}}


def _mock_airdrop_list(url: str, timeout: int = 0, headers: dict | None = None):  # pylint: disable=unused-argument
    mock_response = Mock()
    if url == AIRDROPS_INDEX:
        mock_response.headers = {'ETag': 'etag'}
        mock_response.text = json.dumps(NOT_CSV_WEBPAGE)
        mock_response.json = lambda: NOT_CSV_WEBPAGE
        return mock_response
    else:  # when CSV is queried, return invalid payload
        mock_response.text = mock_response.content = b'<>invalid CSV<>'
        return mock_response


def prepare_airdrop_mock_response(
        url: str,
        mock_airdrop_index: dict,
        mock_airdrop_data: dict,
        update_airdrop_index: bool = False,
):
    """Mocking the airdrop data is very convenient here because the airdrop data is quite large
    and read timeout errors can happen even with 90secs threshold. Vcr-ing it is not possible
    because the vcr yaml file is above the github limit of 100MB. The schema of AIRDROPS_INDEX
    is checked in the rotki/data repo."""
    mock_response = Mock()
    if update_airdrop_index is True:
        mock_airdrop_index['airdrops']['diva']['file_hash'] = 'updated_hash'
        mock_airdrop_index['poap_airdrops']['aave_v2_pioneers'][3] = 'updated_hash'
        mock_response.headers = {'ETag': 'updated_etag'}
    url_to_data_map = {
        AIRDROPS_INDEX: mock_airdrop_index,
        **dict(mock_airdrop_data.items()),
    }

    if url == AIRDROPS_INDEX:
        mock_response.text = json.dumps(mock_airdrop_index)
        mock_response.json = lambda: mock_airdrop_index
        mock_response.headers = {'ETag': 'etag'}
    elif url.startswith('https://claims.eigenfoundation.org'):
        if url.endswith(TEST_ADDR2):
            mock_response.text = """{"queryId":"1714640773899","status":"Complete","data":{"pipelines":{"tokenQualified":10}}}"""  # noqa: E501
        else:
            mock_response.text = """{"queryId":"1714651721784","status":"Complete","data":{"pipelines":{"tokenQualified":0}}}"""  # noqa: E501
        mock_response.json = lambda: json.loads(mock_response.text)
        mock_response.status_code = HTTPStatus.OK
    elif '.parquet' in url:
        mock_response.text = url_to_data_map.get(url, 'address,tokens\n')  # Return the data from the dictionary or just a header if 'url' is not found  # noqa: E501
        parquet_file = BytesIO()
        pl.read_csv(StringIO(mock_response.text), infer_schema_length=0).write_parquet(parquet_file)  # noqa: E501
        parquet_file.seek(0)
        mock_response.content = parquet_file.read()
    else:
        mock_response.text = url_to_data_map.get(url, 'address,tokens\n')  # Return the data from the dictionary or just a header if 'url' is not found  # noqa: E501
        assert isinstance(mock_response.text, str)
        mock_response.content = mock_response.text.encode('utf-8')
    return mock_response


@pytest.mark.freeze_time
@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('new_asset_data', [{
    'asset_type': 'EVM_TOKEN',  # test with EVM token
    'address': '0xe485E2f1bab389C08721B291f6b59780feC83Fd7',
    'name': 'Shutter',
    'symbol': 'SHU',
    'chain_id': 1,
    'decimals': 18,
    'coingecko': 'shutter',
    'cryptocompare': 'SHUTTER',
}, {
    'asset_type': 'OTHER',  # test with non EVM token
    'name': 'Some Non EVM Token',
    'symbol': 'NONEVM',
    'coingecko': 'nonevm',
    'cryptocompare': 'NONEVM',
}])
@pytest.mark.parametrize('remove_global_assets', [['eip155:1/erc20:0xe485E2f1bab389C08721B291f6b59780feC83Fd7']])  # noqa: E501
def test_check_airdrops(
        freezer,
        ethereum_accounts,
        database,
        globaldb,
        new_asset_data,
        data_dir,
):
    # create airdrop claim events to test the claimed attribute
    tolerance_for_amount_check = FVal('0.1')
    claim_events = [
        EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(1594500575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_UNI,
            amount=FVal('400') + tolerance_for_amount_check * FVal('0.25'),  # inside tolerance
            location_label=string_to_evm_address(TEST_ADDR1),
            extra_data={AIRDROP_IDENTIFIER_KEY: 'uniswap'},
        ), EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(1594500575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_1INCH,
            amount=FVal('630.374421472277638654') + tolerance_for_amount_check * FVal('2'),
            location_label=string_to_evm_address(TEST_ADDR1),
            extra_data={AIRDROP_IDENTIFIER_KEY: '1inch'},
        ), EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(1594500575000),
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=Asset('eip155:8453/erc20:0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed'),
            amount=FVal('394857.029384576349787465'),
            location_label=string_to_evm_address(TEST_ADDR2),
            extra_data={AIRDROP_IDENTIFIER_KEY: 'degen2_season1'},
        ),
    ]
    MOCK_AIRDROP_INDEX['airdrops']['shutter']['new_asset_data'] = new_asset_data
    mock_airdrop_index = deepcopy(MOCK_AIRDROP_INDEX)

    new_asset_identifier = MOCK_AIRDROP_INDEX['airdrops']['shutter']['asset_identifier']
    AssetResolver.assets_cache.clear()  # remove new asset from cache

    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(write_cursor, claim_events)

    mock_airdrop_data = {
        f'{AIRDROPS_REPO_BASE}/airdrops/uniswap.parquet':
            f'address,uni,is_lp,is_user,is_socks\n{TEST_ADDR1},400,False,True,False\n{TEST_ADDR2},400.050642,True,True,False\n',
        f'{AIRDROPS_REPO_BASE}/airdrops/1inch.parquet':
            f'address,tokens\n{TEST_ADDR1},630.374421472277638654\n',
        f'{AIRDROPS_REPO_BASE}/airdrops/shapeshift.parquet':
            f'address,tokens\n{TEST_ADDR1},200\n',
        f'{AIRDROPS_REPO_BASE}/airdrops/cow_gnosis.parquet':
            f'address,tokens\n{TEST_ADDR1},99807039723201809834\n',
        f'{AIRDROPS_REPO_BASE}/airdrops/diva.parquet':
            f'address,tokens\n{TEST_ADDR1},84000\n',
        f'{AIRDROPS_REPO_BASE}/airdrops/grain_iou.parquet':
            f'address,tokens\n{TEST_ADDR2},16301717650649890035791\n',
        f'{AIRDROPS_REPO_BASE}/airdrops/shutter.parquet':
            f'address,tokens\n{TEST_ADDR2},394857.029384576349787465\n',
        f'{AIRDROPS_REPO_BASE}/airdrops/poap/poap_aave_v2_pioneers.json':
            f'{{"{TEST_POAP1}": [\n566\n]}}',
        f'{AIRDROPS_REPO_BASE}/airdrops/debridge_1.parquet':
            f'address,tokens\n{TEST_ADDR2},1234.5678\n',
        f'{AIRDROPS_REPO_BASE}/airdrops/degen2_season1.parquet':
            f'address,tokens\n{TEST_ADDR2},394857.029384576349787465\n',
        f'{AIRDROPS_REPO_BASE}/airdrops/degen2_season3.parquet':
            f'address,tokens\n{TEST_ADDR2},394857.029384576349787465\n',
    }

    def mock_requests_get(url: str, timeout: int = 0, headers: dict | None = None):  # pylint: disable=unused-argument
        return prepare_airdrop_mock_response(
            url=url,
            mock_airdrop_index=mock_airdrop_index,
            mock_airdrop_data=mock_airdrop_data,
        )

    # invalid metadata index is already present
    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=(CacheType.AIRDROPS_METADATA,),
            value='{"metadata": "invalid"}',
        )

    # no CSV hashes are present in the DB
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM unique_cache WHERE key LIKE ?', ('AIRDROPS_HASH%',),
        ).fetchone()[0] == 0

    # one CSV is already present with invalid content, but no cached hash in DB
    csv_dir = data_dir / APPDIR_NAME / AIRDROPSDIR_NAME
    csv_dir.mkdir(parents=True, exist_ok=True)
    Path(csv_dir / 'shapeshift.parquet').write_text('invalid,csv\n', encoding='utf8')

    # testing just on the cutoff time of shutter
    freezer.move_to(datetime.datetime.fromtimestamp(1721000000, tz=datetime.UTC))
    with (
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=mock_requests_get),
        patch('rotkehlchen.chain.ethereum.airdrops.check_linea_airdrop', side_effect=lambda addresses, database, found_data: found_data),  # noqa: E501
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
            tolerance_for_amount_check=tolerance_for_amount_check,
        )

    # invalid metadata index is replaced by the valid one
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.AIRDROPS_METADATA,),
        ) == json.dumps(MOCK_AIRDROP_INDEX)

    # new CSV hashes are saved in the DB
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM unique_cache WHERE key LIKE ?', ('AIRDROPS_HASH%',),
        ).fetchone()[0] == 13
        assert cursor.execute(
            'SELECT value FROM unique_cache WHERE key=?', ('AIRDROPS_HASHdiva.parquet',),
        ).fetchone()[0] == MOCK_AIRDROP_INDEX['airdrops']['diva']['file_hash']

    # invalid CSV is also, updated
    assert pl.read_parquet(csv_dir / 'shapeshift.parquet').rows() == [(TEST_ADDR1, '200')]

    # verify new asset's presence and details
    new_found_asset = AssetResolver.resolve_asset(new_asset_identifier).resolve_to_crypto_asset()
    assert new_found_asset.name == new_asset_data['name']
    assert new_found_asset.symbol == new_asset_data['symbol']
    assert new_found_asset.coingecko == new_asset_data['coingecko']
    assert new_found_asset.cryptocompare == new_asset_data['cryptocompare']

    # Test data is returned for the address correctly
    assert len(data) == 3
    assert len(data[TEST_ADDR1]) == 5
    assert data[TEST_ADDR1]['uniswap'] == {
        'amount': '400',
        'asset': A_UNI,
        'link': 'https://app.uniswap.org/',
        'icon': 'uniswap.svg',
        'claimed': True,
        'has_decoder': True,
    }
    assert data[TEST_ADDR1]['1inch'] == {
        'amount': '630.374421472277638654',
        'asset': A_1INCH,
        'link': 'https://1inch.exchange/',
        'icon': '1inch.svg',
        'claimed': False,
        'has_decoder': True,
    }

    assert len(data[TEST_ADDR2]) == 7
    assert data[TEST_ADDR2]['uniswap'] == {
        'amount': '400.050642',
        'asset': A_UNI,
        'link': 'https://app.uniswap.org/',
        'icon': 'uniswap.svg',
        'claimed': False,
        'has_decoder': True,
    }
    assert data[TEST_ADDR2]['grain'] == {
        'amount': '16301.717650649890035791',
        'asset': Asset('eip155:1/erc20:0x6589fe1271A0F29346796C6bAf0cdF619e25e58e'),
        'link': 'https://claim.harvest.finance/',
        'icon': 'grain.png',
        'claimed': False,
        'icon_url': f'{AIRDROPS_REPO_BASE}/airdrops/icons/grain.svg',
        'has_decoder': True,
    }
    assert data[TEST_ADDR2]['shutter'] == {
        'amount': '394857.029384576349787465',
        'asset': A_SHU,
        'link': 'https://claim.shutter.network/',
        'icon': 'shutter.png',
        'claimed': False,
        'cutoff_time': 1721000000,
        'has_decoder': True,
    }
    assert data[TEST_ADDR2]['degen2_season1'] == {
        'amount': '394857.029384576349787465',
        'asset': Asset('eip155:8453/erc20:0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed'),
        'link': 'https://www.degen.tips/airdrop2/season1',
        'icon': 'degen.svg',
        'claimed': True,
        'has_decoder': True,
        'icon_url': 'https://raw.githubusercontent.com/rotki/data/develop/airdrops/icons/degen.svg',
    }
    assert data[TEST_ADDR2]['degen2_season3'] == {
        'amount': '394857.029384576349787465',
        'asset': Asset('eip155:8453/erc20:0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed'),
        'link': 'https://www.degen.tips/airdrop2/season3',
        'icon': 'degen.svg',
        'claimed': False,
        'has_decoder': True,
        'cutoff_time': 1716940800,
        'icon_url': 'https://raw.githubusercontent.com/rotki/data/develop/airdrops/icons/degen.svg',
    }
    assert data[TEST_ADDR2]['debridge_1'] == {
        'amount': '1234.5678',
        'asset': Asset('solana/token:DBRiDgJAMsM95moTzJs7M9LnkGErpbv9v6CUR1DXnUu5'),
        'link': 'https://debridge.foundation/',
        'claimed': False,
        'has_decoder': True,
        'icon_url': 'https://raw.githubusercontent.com/rotki/data/develop/airdrops/icons/debridge.svg',
        'icon': 'debridge.svg',
    }
    assert data[TEST_ADDR2]['eigen'] == {
        'amount': '10',
        'asset': Asset('EIGEN_TOKEN_PRE_RELEASE'),
        'link': 'https://eigenfoundation.org',
        'icon': 'eigen.svg',
        'claimed': False,
        'icon_url': 'https://raw.githubusercontent.com/rotki/data/develop/airdrops/icons/eigen.svg',
        'has_decoder': True,
    }
    assert len(data[TEST_POAP1]) == 1
    assert data[TEST_POAP1]['poap'] == [{
        'event': 'aave_v2_pioneers',
        'assets': [566],
        'link': 'https://poap.delivery/aave-v2-pioneers',
        'name': 'AAVE V2 Pioneers',
    }]

    def update_mock_requests_get(url: str, timeout: int = 0, headers: dict | None = None):  # pylint: disable=unused-argument
        return prepare_airdrop_mock_response(
            url=url,
            mock_airdrop_index=mock_airdrop_index,
            mock_airdrop_data=mock_airdrop_data,
            update_airdrop_index=True,
        )

    freezer.move_to(datetime.datetime.fromtimestamp(1721000001 + 12 * HOUR_IN_SECONDS, tz=datetime.UTC))  # noqa: E501
    with (
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=update_mock_requests_get) as mock_get,  # noqa: E501
        patch('rotkehlchen.chain.ethereum.airdrops.check_linea_airdrop', side_effect=lambda addresses, database, found_data: found_data),  # noqa: E501
    ):
        data = check_airdrops(
            addresses=[TEST_ADDR2],
            database=database,
            tolerance_for_amount_check=tolerance_for_amount_check,
        )
        # diva CSV and aave JSON were queried again because their hashes were updated
        assert mock_get.call_count == 4

    # new CSV hashes are saved in the DB
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT value FROM unique_cache WHERE key=?', ('AIRDROPS_HASHdiva.parquet',),
        ).fetchone()[0] == 'updated_hash'

    # Test cache file and row is created
    for protocol_name, data in MOCK_AIRDROP_INDEX['airdrops'].items():
        if 'file_path' in data:
            assert (data_dir / APPDIR_NAME / AIRDROPSDIR_NAME / f'{protocol_name}.parquet').is_file()  # noqa: E501
    for protocol_name in MOCK_AIRDROP_INDEX['poap_airdrops']:
        assert (data_dir / APPDIR_NAME / AIRDROPSPOAPDIR_NAME / f'{protocol_name}.json').is_file()
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.AIRDROPS_METADATA,),
        ) == rlk_jsondumps(mock_airdrop_index)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_airdrop_fail(database):
    with (
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=_mock_airdrop_list),
        pytest.raises(RemoteError),
    ):
        check_airdrops(addresses=[TEST_ADDR1], database=database)


@pytest.mark.parametrize('remote_etag', ['etag', 'updated_etag'])
@pytest.mark.parametrize('database_etag', [None, 'etag', 'updated_etag'])
def test_fetch_airdrops_metadata(database, remote_etag, database_etag):
    if database_etag is not None:
        # if database_etag is present, add those values in DB
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.AIRDROPS_HASH, ETAG_CACHE_KEY),
                value=database_etag,
            )
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.AIRDROPS_METADATA,),
                value=rlk_jsondumps(MOCK_AIRDROP_INDEX),
            )

    mock_airdrop_index = MOCK_AIRDROP_INDEX
    if remote_etag != database_etag:  # if etag is different, update mock_airdrop_index
        mock_airdrop_index['airdrops']['diva']['name'] = 'new_name'

    def _mock_get(url: str, timeout: int = 0, headers: dict | None = None):  # pylint: disable=unused-argument
        mock_response = Mock()
        mock_response.headers = {'ETag': remote_etag}
        if database_etag == remote_etag:  # not returning content in this case
            mock_response.status_code = HTTPStatus.NOT_MODIFIED
        else:
            mock_response.status_code = HTTPStatus.OK
            mock_response.text = rlk_jsondumps(mock_airdrop_index)
            mock_response.json = lambda: mock_airdrop_index
        return mock_response

    with patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=_mock_get):
        metadata = fetch_airdrops_metadata(database)
        assert metadata == (
            _parse_airdrops(database=database, airdrops_data=mock_airdrop_index['airdrops']),
            mock_airdrop_index['poap_airdrops'],
        )
        if remote_etag != database_etag:  # check if the value is updated
            assert metadata[0]['diva'].name == 'new_name'


@pytest.mark.vcr
def test_check_linea_airdrop(database: 'DBHandler') -> None:
    """Test that the Linea airdrop is correctly detected."""
    assert check_linea_airdrop(
        addresses=[
            string_to_evm_address('0xf1952F8622949F6B865497459453BE7ee0Ae1753'),  # unclaimed
            string_to_evm_address('0x706A70067BE19BdadBea3600Db0626859Ff25D74'),  # no allocation
            string_to_evm_address('0xcD1b393e15e2E6A4b8DF0aED618E6C18221BfD10'),  # claimed
        ],
        database=database,
        found_data=defaultdict(lambda: defaultdict(dict)),
    ) == {
        '0xf1952F8622949F6B865497459453BE7ee0Ae1753': {'linea': {
            'amount': '95894.881636554',
            'asset': (a_linea := Asset('eip155:59144/erc20:0x1789e0043623282D5DCc7F213d703C6D8BAfBB04')),  # noqa: E501
            'link': 'https://linea.build/hub/airdrop',
            'icon': 'linea.svg',
            'claimed': False,
            'has_decoder': True,
            'cutoff_time': 1765324740,
        }},
        '0xcD1b393e15e2E6A4b8DF0aED618E6C18221BfD10': {'linea': {
            'amount': '1045.355540128',
            'asset': a_linea,
            'link': 'https://linea.build/hub/airdrop',
            'icon': 'linea.svg',
            'claimed': True,
            'has_decoder': True,
            'cutoff_time': 1765324740,
        }},
    }
