import json
import random
import re
from collections.abc import Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset, CryptoAsset, EvmToken, UnderlyingToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_GLM
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.globaldb.asset_updates.manager import ASSETS_VERSION_KEY
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION, GlobalDBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChainID, Timestamp, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def count_total_assets() -> int:
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM assets')
        return cursor.fetchone()[0]


def mock_asset_updates(original_requests_get: Callable[..., requests.Response], latest: int, updates: dict[str, Any], sql_actions: dict[str, dict[str, str]]) -> Any:  # noqa: E501

    def mock_requests_get(url: str, *args: Any, **kwargs: Any) -> requests.Response | MockResponse:  # pylint: disable=unused-argument
        if 'github' not in url:
            return original_requests_get(url, *args, **kwargs)

        if 'updates/info.json' in url:
            response = f'{{"latest": {latest}, "updates": {json.dumps(updates)}}}'
        elif 'updates.sql' in url:
            match = re.search(r'.*/(\d+)/(.*)?updates.sql', url)
            assert match, f'Couldnt extract version from {url}'
            version = match.group(1)
            action_set = sql_actions.get(version)
            assert action_set is not None, f'Could not find SQL set for version {version}'
            if 'mapping' in url:
                action = action_set.get('mappings')
            elif 'collection' in url:
                action = action_set.get('collections')
            else:
                action = action_set.get('assets')
            assert action is not None, f'Could not find SQL action for version {version}'
            response = action
        else:
            raise AssertionError(f'Unrecognized argument url for assets update mock in tests: {url}')  # noqa: E501

        return MockResponse(200, response)

    return patch('requests.get', side_effect=mock_requests_get)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_simple_update(rotkehlchen_api_server: 'APIServer', globaldb: GlobalDBHandler) -> None:
    """Test that the happy case of update works.

    - Test that up_to_version argument works
    - Test that only versions above current local are applied
    - Test that versions with min/max schema mismatch are skipped
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_4_assets = """INSERT INTO assets(identifier, name, type) VALUES('eip155:1/erc20:0xC2FEC534c461c45533e142f724d0e3930650929c', 'AKB token', 'C');INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES('eip155:1/erc20:0xC2FEC534c461c45533e142f724d0e3930650929c', 'A', 1, '0xC2FEC534c461c45533e142f724d0e3930650929c', 18, NULL);INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('eip155:1/erc20:0xC2FEC534c461c45533e142f724d0e3930650929c', 'AKB', NULL, 'AIDU', NULL, 123, NULL);
*
INSERT INTO assets(identifier, name, type) VALUES('121-ada-FADS-as', 'A name', 'F'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('121-ada-FADS-as', 'SYMBOL', '', '', 'BTC', NULL, NULL);
*
UPDATE assets SET name='Ευρώ' WHERE identifier='EUR';
INSERT INTO assets(identifier, name, type) VALUES('EUR', 'Ευρώ', 'A'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('EUR', 'Ευρώ', 'EUR', NULL, NULL, NULL, NULL, NULL);
    """  # noqa: E501
    # The update_4_assets has an extra newline which is put there on purpose to see
    # that the consuming logic can handle trailing newlines
    update_4_collections = """INSERT INTO asset_collections(id, name, symbol, main_asset) VALUES (99999999, 'My custom ETH', 'ETHS', 'ETHS')
    *
    UPDATE asset_collections SET name='updated collection' WHERE id=33
    *
    DELETE FROM asset_collections WHERE id=39;
    *
    """  # noqa: E501
    update_4_mappings = """INSERT INTO multiasset_mappings(collection_id, asset) VALUES (99999999, 'ETH');
    *
    INSERT INTO multiasset_mappings(collection_id, asset) VALUES (99999999, 'eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84');
    *
    DELETE FROM multiasset_mappings WHERE collection_id=314 AND asset='eip155:10/erc20:0xC52D7F23a2e460248Db6eE192Cb23dD12bDDCbf6';
    *
    """  # noqa: E501

    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT name FROM asset_collections WHERE id=33',
        ).fetchone()[0] == 'STASIS EURS'
        assert cursor.execute(
            "SELECT COUNT(*) FROM multiasset_mappings WHERE collection_id=314 AND "
            "asset='eip155:10/erc20:0xC52D7F23a2e460248Db6eE192Cb23dD12bDDCbf6'",
        ).fetchone()[0] == 1

    empty_update = {'mappings': '', 'collections': '', 'assets': ''}
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999996,
        updates={
            '999999991': {
                'changes': 1,
                'min_schema_version': GLOBAL_DB_VERSION,
                'max_schema_version': GLOBAL_DB_VERSION,
            },
            '999999992': {
                'changes': 1,
                'min_schema_version': GLOBAL_DB_VERSION,
                'max_schema_version': GLOBAL_DB_VERSION,
            },
            '999999993': {
                'changes': 5,
                'min_schema_version': GLOBAL_DB_VERSION - 2,
                'max_schema_version': GLOBAL_DB_VERSION - 1,
            },
            '999999994': {
                'changes': 3,
                'min_schema_version': GLOBAL_DB_VERSION,
                'max_schema_version': GLOBAL_DB_VERSION,
            },
            '999999995': {
                'changes': 2,
                'min_schema_version': GLOBAL_DB_VERSION,
                'max_schema_version': GLOBAL_DB_VERSION,
            },
            '999999996': {
                'changes': 5,
                'min_schema_version': GLOBAL_DB_VERSION + 1,
                'max_schema_version': GLOBAL_DB_VERSION + 2,
            },
            '999999997': {
                'changes': 5,
                'min_schema_version': GLOBAL_DB_VERSION + 1,
                'max_schema_version': GLOBAL_DB_VERSION + 2,
            },
        },
        sql_actions={'999999991': empty_update, '999999992': empty_update, '999999993': empty_update, '999999994': {'assets': update_4_assets, 'collections': update_4_collections, 'mappings': update_4_mappings}, '999999995': empty_update, '999999996': empty_update},  # noqa: E501
    )
    globaldb.add_setting_value(ASSETS_VERSION_KEY, 999999992)
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            result = outcome['result']
            assert outcome['message'] == ''
        else:
            result = assert_proper_sync_response_with_result(response)
        assert result['local'] == 999999992
        assert result['remote'] == 999999996
        assert result['new_changes'] == 5  # 994 (3) + 995(2)

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query, 'up_to_version': 999999997},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_sync_response_with_result(response)

        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()

        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 2
        assert f'Skipping assets update 999999993 since it requires a min schema of {GLOBAL_DB_VERSION - 2} and max schema of {GLOBAL_DB_VERSION - 1} while the local DB schema version is {GLOBAL_DB_VERSION}. You will have to follow an alternative method to obtain the assets of this update. Easiest would be to reset global DB' in warnings[0]  # noqa: E501
        assert f'Skipping assets update 999999996 since it requires a min schema of {GLOBAL_DB_VERSION + 1}. Please upgrade rotki to get this assets update' in warnings[1]  # noqa: E501

        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 999999995
        new_token = EvmToken('eip155:1/erc20:0xC2FEC534c461c45533e142f724d0e3930650929c')
        assert new_token.identifier == strethaddress_to_identifier('0xC2FEC534c461c45533e142f724d0e3930650929c')  # noqa: E501
        assert new_token.name == 'AKB token'
        assert new_token.symbol == 'AKB'
        assert new_token.asset_type == AssetType.EVM_TOKEN
        assert new_token.started == 123
        assert new_token.forked is None
        assert new_token.swapped_for is None
        assert new_token.coingecko is None
        assert new_token.cryptocompare == 'AIDU'
        assert new_token.evm_address == '0xC2FEC534c461c45533e142f724d0e3930650929c'
        assert new_token.decimals == 18
        assert new_token.protocol is None

        new_asset = CryptoAsset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''

        assert Asset('EUR').resolve_to_asset_with_name_and_type().name == 'Ευρώ'

        with globaldb.conn.read_ctx() as cursor:
            cursor.execute('SELECT * FROM asset_collections WHERE id = 99999999')
            assert cursor.fetchall() == [(99999999, 'My custom ETH', 'ETHS', 'ETHS')]
            cursor.execute('SELECT * FROM multiasset_mappings WHERE collection_id = 99999999')
            assert cursor.fetchall() == [(99999999, 'ETH'), (99999999, 'eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')]  # noqa: E501
            assert cursor.execute(
                'SELECT name, symbol FROM asset_collections WHERE id=33',
            ).fetchone() == ('updated collection', 'EURS')
            assert cursor.execute(
                "SELECT COUNT(*) FROM multiasset_mappings WHERE collection_id=314 AND "
                "asset='eip155:10/erc20:0xC52D7F23a2e460248Db6eE192Cb23dD12bDDCbf6'",
            ).fetchone()[0] == 0
            assert cursor.execute(
                'SELECT COUNT(*) FROM asset_collections WHERE id=39',
            ).fetchone()[0] == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_update_conflicts(rotkehlchen_api_server: 'APIServer', globaldb: GlobalDBHandler) -> None:
    """Test that conflicts in an asset update are handled properly"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_1 = """INSERT INTO assets(identifier, name, type) VALUES('121-ada-FADS-as', 'A name', 'F'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('121-ada-FADS-as', 'SYMBOL', '', '', 'BTC', NULL, NULL);
*
INSERT INTO assets(identifier, name, type) VALUES('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', 'New Multi Collateral DAI', 'C');INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', 'A', 1, '0x6B175474E89094C44Da98b954EedeAC495271d0F', 8, 'maker'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', 'NDAI', 'dai', NULL, NULL, 1573672677, NULL)
*
INSERT INTO assets(identifier, name, type) VALUES('DASH', 'Dash', 'B'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('DASH', 'DASH', 'dash-coingecko', NULL, 'BTC', 1337, NULL);
*
INSERT INTO assets(identifier, name, type) VALUES('eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F', 'Conflicting token', 'C');INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES('eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F', 'A', 1, '0x1B175474E89094C44Da98b954EedeAC495271d0F', 18, NULL);INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F', 'CTK', 'ctk', NULL, NULL, 1573672677, NULL)
*
    """  # noqa: E501
    # add a conflicting token
    globaldb.add_asset(EvmToken.initialize(
        address=string_to_evm_address('0x1B175474E89094C44Da98b954EedeAC495271d0F'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=12,
        name='Conflicting token',
        symbol='CTK',
        started=None,
        swapped_for=None,
        coingecko='ctk',
        cryptocompare=None,
        protocol=None,
        underlying_tokens=None,
    ))
    globaldb.add_user_owned_assets([Asset('eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F')])
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999991,
        updates={'999999991': {
            'changes': 3,
            'min_schema_version': GLOBAL_DB_VERSION,
            'max_schema_version': GLOBAL_DB_VERSION,
        }},
        sql_actions={'999999991': {'assets': update_1, 'collections': '', 'mappings': ''}},
    )
    globaldb.add_setting_value(ASSETS_VERSION_KEY, 999999990)
    start_assets_num = count_total_assets()
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            result = outcome['result']
            assert outcome['message'] == ''
        else:
            result = assert_proper_sync_response_with_result(response)
        assert result['local'] == 999999990
        assert result['remote'] == 999999991
        assert result['new_changes'] == 3

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == 'Found conflicts during assets upgrade'
            result = outcome['result']
        else:
            result = assert_proper_sync_response_with_result(
                response,
                message='Found conflicts during assets upgrade',
                status_code=HTTPStatus.CONFLICT,
            )

        # Make sure that nothing was committed
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 999999990
        assert count_total_assets() == start_assets_num
        with pytest.raises(UnknownAsset):
            Asset('121-ada-FADS-as').resolve_to_asset_with_name_and_type()
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        # See that we get 3 conflicts
        expected_result = [{
            'identifier': 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'local': {
                'name': 'Multi Collateral Dai',
                'symbol': 'DAI',
                'asset_type': 'evm token',
                'started': 1573672677,
                'forked': None,
                'swapped_for': None,
                'address': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                'evm_chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': 'DAI',
                'coingecko': 'dai',
                'protocol': None,
            },
            'remote': {
                'name': 'New Multi Collateral DAI',
                'symbol': 'NDAI',
                'asset_type': 'evm token',
                'started': 1573672677,
                'forked': None,
                'swapped_for': None,
                'address': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                'evm_chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 8,
                'cryptocompare': None,
                'coingecko': 'dai',
                'protocol': 'maker',
            },
        }, {
            'identifier': 'DASH',
            'local': {
                'name': 'Dash',
                'symbol': 'DASH',
                'asset_type': 'own chain',
                'started': 1390095618,
                'forked': None,
                'swapped_for': None,
                'address': None,
                'token_kind': None,
                'decimals': None,
                'cryptocompare': 'DASH',
                'coingecko': 'dash',
                'protocol': None,
            },
            'remote': {
                'name': 'Dash',
                'symbol': 'DASH',
                'asset_type': 'own chain',
                'started': 1337,
                'forked': 'BTC',
                'swapped_for': None,
                'address': None,
                'token_kind': None,
                'decimals': None,
                'cryptocompare': None,
                'coingecko': 'dash-coingecko',
                'protocol': None,
            },
        }, {
            'identifier': 'eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F',
            'local': {
                'asset_type': 'evm token',
                'coingecko': 'ctk',
                'cryptocompare': None,
                'decimals': 12,
                'address': '0x1B175474E89094C44Da98b954EedeAC495271d0F',
                'evm_chain': 'ethereum',
                'token_kind': 'erc20',
                'forked': None,
                'name': 'Conflicting token',
                'protocol': None,
                'started': None,
                'swapped_for': None,
                'symbol': 'CTK',
            },
            'remote': {
                'asset_type': 'evm token',
                'coingecko': 'ctk',
                'cryptocompare': None,
                'decimals': 18,
                'address': '0x1b175474E89094C44DA98B954EeDEAC495271d0f',
                'evm_chain': 'ethereum',
                'token_kind': 'erc20',
                'forked': None,
                'name': 'Conflicting token',
                'protocol': None,
                'started': 1573672677,
                'swapped_for': None,
                'symbol': 'CTK',
            },
        }]
        assert result == expected_result

        # now try the update again but specify the conflicts resolution
        conflicts = {'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F': 'remote', 'DASH': 'local', 'eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F': 'remote'}  # noqa: E501
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query, 'conflicts': conflicts},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_sync_response_with_result(
                response,
                message='',
                status_code=HTTPStatus.OK,
            )

        cursor = globaldb.conn.cursor()
        # check conflicts were solved as per the given choices and new asset also added
        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 999999991
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        dai = EvmToken('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F')
        assert dai.identifier == strethaddress_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F')  # noqa: E501
        assert dai.name == 'New Multi Collateral DAI'
        assert dai.symbol == 'NDAI'
        assert dai.asset_type == AssetType.EVM_TOKEN
        assert dai.started == 1573672677
        assert dai.forked is None
        assert dai.swapped_for is None
        assert dai.coingecko == 'dai'
        assert dai.cryptocompare is None
        assert dai.evm_address == '0x6B175474E89094C44Da98b954EedeAC495271d0F'
        assert dai.decimals == 8
        assert dai.protocol == 'maker'
        # make sure data is in both tables
        assert cursor.execute('SELECT COUNT(*) from evm_tokens WHERE address=?', ('0x6B175474E89094C44Da98b954EedeAC495271d0F',)).fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier=?', ('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',)).fetchone()[0] == 1  # noqa: E501

        dash = CryptoAsset('DASH')
        assert dash.identifier == 'DASH'
        assert dash.name == 'Dash'
        assert dash.symbol == 'DASH'
        assert dash.asset_type == AssetType.OWN_CHAIN
        assert dash.started == 1390095618
        assert dash.forked is None
        assert dash.swapped_for is None
        assert dash.coingecko == 'dash'
        assert dash.cryptocompare == 'DASH'
        assert cursor.execute('SELECT COUNT(*) from common_asset_details WHERE identifier=?', ('DASH',)).fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier=?', ('DASH',)).fetchone()[0] == 1  # noqa: E501

        new_asset = CryptoAsset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''
        assert cursor.execute('SELECT COUNT(*) from common_asset_details WHERE identifier=?', ('121-ada-FADS-as',)).fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier=?', ('121-ada-FADS-as',)).fetchone()[0] == 1  # noqa: E501

        ctk = EvmToken('eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F')
        assert ctk.name == 'Conflicting token'
        assert ctk.symbol == 'CTK'
        assert ctk.asset_type == AssetType.EVM_TOKEN
        assert ctk.started == 1573672677
        assert ctk.forked is None
        assert ctk.swapped_for is None
        assert ctk.coingecko == 'ctk'
        assert ctk.cryptocompare is None
        assert ctk.evm_address == '0x1B175474E89094C44Da98b954EedeAC495271d0F'
        assert ctk.decimals == 18
        assert ctk.protocol is None
        assert cursor.execute('SELECT COUNT(*) from evm_tokens WHERE address=?', ('0x1B175474E89094C44Da98b954EedeAC495271d0F',)).fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier=?', ('eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F',)).fetchone()[0] == 1  # noqa: E501


@pytest.mark.skip('Broken after changes in the assets. Check #4876')
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_foreignkey_conflict(
        rotkehlchen_api_server: 'APIServer',
        globaldb: GlobalDBHandler,
) -> None:
    """Test that when a conflict that's not solvable happens the entry is ignored

    One such case is when the update of an asset would violate a foreign key constraint.
    So we try to update the swapped_for to a non existing asset and make sure it's skipped.
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_1 = """INSERT INTO assets(identifier, name, type) VALUES("121-ada-FADS-as", "A name", "F"); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("121-ada-FADS-as", "SYMBOL", "", "", "BTC", NULL, NULL);
*
UPDATE assets SET swapped_for="eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972" WHERE identifier="eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d";
INSERT INTO assets(identifier, name, type) VALUES("eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "Golem", "C");INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES("eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "A", 1, "0xa74476443119A942dE498590Fe1f2454d7D4aC0d", 18, NULL); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "GNT", "golem", NULL, NULL, 1478810650, "eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972")
    """  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999991,
        updates={'999999991': {
            'changes': 2,
            'min_schema_version': GLOBAL_DB_VERSION,
            'max_schema_version': GLOBAL_DB_VERSION,
        }},
        sql_actions={'999999991': {'assets': update_1, 'collections': '', 'mappings': ''}},
    )
    globaldb.add_setting_value(ASSETS_VERSION_KEY, 999999990)
    start_assets_num = count_total_assets()
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            result = outcome['result']
            assert outcome['message'] == ''
        else:
            result = assert_proper_sync_response_with_result(response)
        assert result['local'] == 999999990
        assert result['remote'] == 999999991
        assert result['new_changes'] == 2

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == 'Found conflicts during assets upgrade'
            result = outcome['result']
        else:
            result = assert_proper_sync_response_with_result(
                response,
                message='Found conflicts during assets upgrade',
                status_code=HTTPStatus.CONFLICT,
            )

        # Make sure that nothing was committed
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 999999990
        assert count_total_assets() == start_assets_num
        with pytest.raises(UnknownAsset):
            Asset('121-ada-FADS-as').resolve_to_asset_with_name_and_type()
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        # See that we get a conflict
        expected_result = [{
            'identifier': 'eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
            'local': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'evm token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': 'eip155:1/erc20:0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429',
                'address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'evm_chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
            'remote': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'evm token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': 'eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972',
                'address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'evm_chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
        }]
        assert result == expected_result

        # now try the update again but specify the conflicts resolution
        conflicts = {'eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d': 'remote'}
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query, 'conflicts': conflicts},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_sync_response_with_result(
                response,
                message='',
                status_code=HTTPStatus.OK,
            )

        # check new asset was added and conflict was ignored with an error due to
        # inability to do anything with the missing swapped_for
        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 999999991
        gnt = EvmToken('eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d')
        assert gnt.identifier == strethaddress_to_identifier('0xa74476443119A942dE498590Fe1f2454d7D4aC0d')  # noqa: E501
        assert gnt.name == 'Golem'
        assert gnt.symbol == 'GNT'
        assert gnt.asset_type == AssetType.EVM_TOKEN
        assert gnt.started == 1478810650
        assert gnt.forked is None
        assert gnt.swapped_for == A_GLM.identifier
        assert gnt.coingecko == 'golem'
        assert gnt.cryptocompare is None
        assert gnt.evm_address == '0xa74476443119A942dE498590Fe1f2454d7D4aC0d'
        assert gnt.decimals == 18
        assert gnt.protocol is None

        new_asset = CryptoAsset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''

        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 1
        assert f'Failed to resolve conflict for {gnt.identifier} in the DB during the v999999991 assets update. Skipping entry' in warnings[0]  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_update_from_early_clean_db(
        rotkehlchen_api_server: 'APIServer',
        globaldb: GlobalDBHandler,
) -> None:
    """
    Test that if the asset upgrade happens from a very early DB that has had no assets
    version key set we still upgrade properly and set the assets version properly.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_15 = """INSERT INTO assets(identifier, name, type) VALUES('121-ada-FADS-as', 'A name', 'F'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('121-ada-FADS-as', 'SYMBOL', '', '', 'BTC', NULL, NULL);
*
UPDATE assets SET swapped_for='eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972' WHERE identifier='eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d';
INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES('eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d', 'A', 1, '0xa74476443119A942dE498590Fe1f2454d7D4aC0d', 18, NULL);INSERT INTO assets(identifier, name, type) VALUES('eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d', 'Golem', 'C'); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d', 'GNT', 'golem', NULL, NULL,1478810650, 'eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972')
    """  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=15,
        updates={'15': {
            'changes': 2,
            'min_schema_version': GLOBAL_DB_VERSION,
            'max_schema_version': GLOBAL_DB_VERSION,
        }},
        sql_actions={'15': {'assets': update_15, 'collections': '', 'mappings': ''}},
    )
    cursor = globaldb.conn.cursor()
    cursor.execute('DELETE FROM settings WHERE name=?', (ASSETS_VERSION_KEY,))
    start_assets_num = count_total_assets()
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
        )
        result = assert_proper_sync_response_with_result(response)
        assert result['local'] == 0
        assert result['remote'] == 15
        assert result['new_changes'] == 2

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
        )
        result = assert_proper_sync_response_with_result(
            response,
            message='Found conflicts during assets upgrade',
            status_code=HTTPStatus.CONFLICT,
        )

        # Make sure that nothing was committed
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 0
        assert count_total_assets() == start_assets_num
        with pytest.raises(UnknownAsset):
            Asset('121-ada-FADS-as').resolve_to_asset_with_name_and_type()
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        # See that we get a conflict
        expected_result = [{
            'identifier': 'eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
            'local': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'evm token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': 'eip155:1/erc20:0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429',
                'address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'evm_chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
            'remote': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'evm token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': 'eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972',
                'address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'evm_chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
        }]
        assert result == expected_result

        # now try the update again but specify the conflicts resolution
        conflicts = {'eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d': 'remote'}
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'conflicts': conflicts},
        )
        result = assert_proper_sync_response_with_result(
            response,
            message='',
            status_code=HTTPStatus.OK,
        )

        # check new asset was added and conflict was ignored with an error due to
        # inability to do anything with the missing swapped_for
        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 15
        # TODO: Needs to be fixed as described in # 4876
        """
        gnt = EvmToken('eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d')
        assert gnt.identifier == strethaddress_to_identifier('0xa74476443119A942dE498590Fe1f2454d7D4aC0d')
        assert gnt.name == 'Golem'
        assert gnt.symbol == 'GNT'
        assert gnt.asset_type == AssetType.EVM_TOKEN
        assert gnt.started == 1478810650
        assert gnt.forked is None
        assert gnt.swapped_for == A_GLM.identifier
        assert gnt.coingecko == 'golem'
        assert gnt.cryptocompare is None
        assert gnt.evm_address == '0xa74476443119A942dE498590Fe1f2454d7D4aC0d'
        assert gnt.decimals == 18
        assert gnt.protocol is None
        """    # noqa: E501

        new_asset = CryptoAsset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''

        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 1
        assert 'Failed to resolve conflict for eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d in the DB during the v15 assets update. Skipping entry' in warnings[0]  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_update_underlying_tokens(rotkehlchen_api_server: 'APIServer', globaldb: GlobalDBHandler) -> None:  # noqa: E501
    """Test that updating underlying tokens is handled properly."""
    update_1 = """DELETE FROM underlying_tokens_list WHERE parent_token_entry="eip155:1/erc20:0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c"; INSERT INTO underlying_tokens_list(identifier, weight, parent_token_entry) VALUES("eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8", "1", "eip155:1/erc20:0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c");
INSERT INTO assets(identifier, name, type) VALUES("eip155:1/erc20:0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c", "yearn Curve.fi yDAI/yUSDC/yUSDT/yTUSD", "C"); INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES("eip155:1/erc20:0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c", "A", 1, "0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c", 18, "yearn_vaults_v1"); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES("eip155:1/erc20:0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c", "yyDAI+yUSDC+yUSDT+yTUSD", "yvault-lp-ycurve", "", NULL, 1596091760, NULL); INSERT INTO underlying_tokens_list(identifier, weight, parent_token_entry) VALUES("eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8", "1", "eip155:1/erc20:0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c");
    """  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999991,
        updates={'999999991': {
            'changes': 1,
            'min_schema_version': GLOBAL_DB_VERSION,
            'max_schema_version': GLOBAL_DB_VERSION,
        }},
        sql_actions={'999999991': {'assets': update_1, 'collections': '', 'mappings': ''}},
    )
    globaldb.add_setting_value(ASSETS_VERSION_KEY, 999999990)
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
        )
        result = assert_proper_sync_response_with_result(response)
        assert result['local'] == 999999990
        assert result['remote'] == 999999991
        assert result['new_changes'] == 1

    token = globaldb.get_evm_token(
        address=string_to_evm_address('0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c'),
        chain_id=ChainID.ETHEREUM,
    )
    assert token is not None
    assert token.underlying_tokens == [UnderlyingToken(
        address=string_to_evm_address('0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8'),
        token_kind=TokenKind.ERC20,
        weight=ONE,
    )]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_update_no_user_loggedin(rotkehlchen_api_server: 'APIServer') -> None:
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetupdatesresource',
        ),
    )
    assert_proper_sync_response_with_result(response)


def test_async_db_reset(rotkehlchen_api_server: 'APIServer') -> None:
    """Test the endpoint for resetting the globaldb using an async task"""
    asset_id = 'my_custom_id'
    GlobalDBHandler.add_asset(CryptoAsset.initialize(
        identifier=asset_id,
        asset_type=AssetType.OWN_CHAIN,
        name='Lolcoin2',
        symbol='LOLZ2',
        started=Timestamp(0),
    ))
    Asset(asset_id).resolve()
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'assetupdatesresource',
        ),
        json={'async_query': True, 'ignore_warnings': True, 'reset': 'hard'},
    )
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(
        rotkehlchen_api_server,
        task_id,
    )
    assert outcome['result'] is True
    assert outcome['message'] == ''

    with pytest.raises(UnknownAsset):
        Asset(asset_id).resolve()
