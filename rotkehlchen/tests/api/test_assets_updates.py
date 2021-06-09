import json
import random
import re
from http import HTTPStatus
from typing import Any, Dict
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.typing import AssetType
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION
from rotkehlchen.globaldb.updates import ASSETS_VERSION_KEY
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import A_GLM
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import ChecksumEthAddress


def mock_asset_updates(original_requests_get, latest: int, updates: Dict[str, Any], sql_actions: Dict[str, str]):  # noqa: E501

    def mock_requests_get(url, *args, **kwargs):  # pylint: disable=unused-argument
        if 'github' not in url:
            return original_requests_get(url, *args, **kwargs)

        if 'updates/info.json' in url:
            response = f'{{"latest": {latest}, "updates": {json.dumps(updates)}}}'
        elif 'updates.sql' in url:
            match = re.search(r'.*/(\d+)/updates.sql', url)
            assert match, f'Couldnt extract version from {url}'
            version = match.group(1)
            action = sql_actions.get(version)
            assert action is not None, f'Could not find SQL action for version {version}'
            response = action
        else:
            raise AssertionError(f'Unrecognized argument url for assets update mock in tests: {url}')  # noqa: E501

        return MockResponse(200, response)

    return patch('requests.get', side_effect=mock_requests_get)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_simple_update(rotkehlchen_api_server, globaldb):
    """Test that the happy case of update works.

    - Test that up_to_version argument works
    - Test that only versions above current local are applied
    - Test that versions with min/max schema mismatch are skipped
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_3 = """INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES("0xC2FEC534c461c45533e142f724d0e3930650929c", 18, NULL);INSERT INTO assets(identifier,type, name, symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("_ceth_0xC2FEC534c461c45533e142f724d0e3930650929c", "C", "AKB token", "AKB",123, NULL,   NULL, "AIDU", "0xC2FEC534c461c45533e142f724d0e3930650929c");
*
INSERT INTO assets(identifier,type,name,symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("121-ada-FADS-as", "F","A name","SYMBOL",NULL, NULL,"", "", "121-ada-FADS-as");INSERT INTO common_asset_details(asset_id, forked) VALUES("121-ada-FADS-as", "BTC");
*
UPDATE assets SET name="Ευρώ" WHERE identifier="EUR";
INSERT INTO assets(identifier,type,name,symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("EUR", "A","Ευρώ","EUR",NULL, NULL,NULL,NULL, "EUR");INSERT INTO common_asset_details(asset_id, forked) VALUES("EUR", NULL);
    """  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999996,
        updates={
            "999999991": {
                "changes": 1,
                "min_schema_version": GLOBAL_DB_VERSION,
                "max_schema_version": GLOBAL_DB_VERSION,
            },
            "999999992": {
                "changes": 1,
                "min_schema_version": GLOBAL_DB_VERSION,
                "max_schema_version": GLOBAL_DB_VERSION,
            },
            "999999993": {
                "changes": 3,
                "min_schema_version": GLOBAL_DB_VERSION,
                "max_schema_version": GLOBAL_DB_VERSION,
            },
            "999999994": {
                "changes": 5,
                "min_schema_version": GLOBAL_DB_VERSION + 1,
                "max_schema_version": GLOBAL_DB_VERSION - 1,
            },
            "999999995": {
                "changes": 5,
                "min_schema_version": GLOBAL_DB_VERSION,
                "max_schema_version": GLOBAL_DB_VERSION,
            },
            "999999996": {
                "changes": 5,
                "min_schema_version": GLOBAL_DB_VERSION,
                "max_schema_version": GLOBAL_DB_VERSION,
            },
        },
        sql_actions={"999999991": "", "999999992": "", "999999993": update_3, "999999994": "", "999999995": ""},  # noqa: E501
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
            result = assert_proper_response_with_result(response)
        assert result['local'] == 999999992
        assert result['remote'] == 999999996
        assert result['new_changes'] == 13  # changes from 99[3 + 4 + 6], skipping 5

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query, 'up_to_version': 999999995},
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
            result = assert_proper_response_with_result(response)

        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 1
        assert 'Skipping assets update 999999994 since it requires a min schema of' in warnings[0]

        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999995
        new_token = EthereumToken('0xC2FEC534c461c45533e142f724d0e3930650929c')
        assert new_token.identifier == strethaddress_to_identifier('0xC2FEC534c461c45533e142f724d0e3930650929c')  # noqa: E501
        assert new_token.name == 'AKB token'
        assert new_token.symbol == 'AKB'
        assert new_token.asset_type == AssetType.ETHEREUM_TOKEN
        assert new_token.started == 123
        assert new_token.forked is None
        assert new_token.swapped_for is None
        assert new_token.coingecko is None
        assert new_token.cryptocompare == 'AIDU'
        assert new_token.ethereum_address == '0xC2FEC534c461c45533e142f724d0e3930650929c'
        assert new_token.decimals == 18
        assert new_token.protocol is None

        new_asset = Asset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''

        assert Asset('EUR').name == 'Ευρώ'


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_update_conflicts(rotkehlchen_api_server, globaldb):
    """Test that conflicts in an asset update are handled properly"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_1 = """INSERT INTO assets(identifier,type,name,symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("121-ada-FADS-as", "F","A name","SYMBOL",NULL, NULL,"", "", "121-ada-FADS-as");INSERT INTO common_asset_details(asset_id, forked) VALUES("121-ada-FADS-as", "BTC");
*
INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES("0x6B175474E89094C44Da98b954EedeAC495271d0F", 8, "maker");INSERT INTO assets(identifier,type, name, symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F", "C", "New Multi Collateral DAI", "NDAI", 1573672677, NULL, "dai", NULL, "0x6B175474E89094C44Da98b954EedeAC495271d0F");
*
INSERT INTO assets(identifier,type,name,symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("DASH", "B","Dash","DASH",1337, NULL, "dash-coingecko", NULL, "DASH");INSERT INTO common_asset_details(asset_id, forked) VALUES("DASH", "BTC");
*
INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES("0x1B175474E89094C44Da98b954EedeAC495271d0F", 18, NULL); INSERT INTO assets(identifier,type, name, symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("_ceth_0x1B175474E89094C44Da98b954EedeAC495271d0F", "C", "Conflicting token", "CTK", 1573672677, NULL, "ctk", NULL, "0x1B175474E89094C44Da98b954EedeAC495271d0F");
*
    """  # noqa: E501
    globaldb.add_asset(  # add a conflicting token
        asset_id='_ceth_0x1B175474E89094C44Da98b954EedeAC495271d0F',
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=EthereumToken.initialize(
            address=ChecksumEthAddress('0x1B175474E89094C44Da98b954EedeAC495271d0F'),
            decimals=12,
            name='Conflicting token',
            symbol='CTK',
            started=None,
            swapped_for=None,
            coingecko='ctk',
            cryptocompare=None,
            protocol=None,
            underlying_tokens=None,
        ),
    )
    globaldb.add_user_owned_assets([Asset('_ceth_0x1B175474E89094C44Da98b954EedeAC495271d0F')])
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999991,
        updates={"999999991": {
            "changes": 3,
            "min_schema_version": GLOBAL_DB_VERSION,
            "max_schema_version": GLOBAL_DB_VERSION,
        }},
        sql_actions={"999999991": update_1},
    )
    globaldb.add_setting_value(ASSETS_VERSION_KEY, 999999990)
    start_assets_num = len(globaldb.get_all_asset_data(mapping=False))
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
            result = assert_proper_response_with_result(response)
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
            result = assert_proper_response_with_result(
                response,
                message='Found conflicts during assets upgrade',
                status_code=HTTPStatus.CONFLICT,
            )

        # Make sure that nothing was committed
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999990
        assert len(globaldb.get_all_asset_data(mapping=False)) == start_assets_num
        with pytest.raises(UnknownAsset):
            Asset('121-ada-FADS-as')
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        # See that we get 3 conflicts
        expected_result = [{
            'identifier': '_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'local': {
                'name': 'Multi Collateral Dai',
                'symbol': 'DAI',
                'asset_type': 'ethereum token',
                'started': 1573672677,
                'forked': None,
                'swapped_for': None,
                'ethereum_address': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'dai',
                'protocol': None,
            },
            'remote': {
                'name': 'New Multi Collateral DAI',
                'symbol': 'NDAI',
                'asset_type': 'ethereum token',
                'started': 1573672677,
                'forked': None,
                'swapped_for': None,
                'ethereum_address': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
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
                'ethereum_address': None,
                'decimals': None,
                'cryptocompare': None,
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
                'ethereum_address': None,
                'decimals': None,
                'cryptocompare': None,
                'coingecko': 'dash-coingecko',
                'protocol': None,
            },
        }, {
            'identifier': '_ceth_0x1B175474E89094C44Da98b954EedeAC495271d0F',
            'local': {
                'asset_type': 'ethereum token',
                'coingecko': 'ctk',
                'cryptocompare': None,
                'decimals': 12,
                'ethereum_address': '0x1B175474E89094C44Da98b954EedeAC495271d0F',
                'forked': None,
                'name': 'Conflicting token',
                'protocol': None,
                'started': None,
                'swapped_for': None,
                'symbol': 'CTK',
            },
            'remote': {
                'asset_type': 'ethereum token',
                'coingecko': 'ctk',
                'cryptocompare': None,
                'decimals': 18,
                'ethereum_address': '0x1b175474E89094C44DA98B954EeDEAC495271d0f',
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
        conflicts = {'_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F': 'remote', 'DASH': 'local', '_ceth_0x1B175474E89094C44Da98b954EedeAC495271d0F': 'remote'}  # noqa: E501
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
            result = assert_proper_response_with_result(
                response,
                message='',
                status_code=HTTPStatus.OK,
            )

        cursor = globaldb._conn.cursor()
        # check conflicts were solved as per the given choices and new asset also added
        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999991
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        dai = EthereumToken('0x6B175474E89094C44Da98b954EedeAC495271d0F')
        assert dai.identifier == strethaddress_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F')  # noqa: E501
        assert dai.name == 'New Multi Collateral DAI'
        assert dai.symbol == 'NDAI'
        assert dai.asset_type == AssetType.ETHEREUM_TOKEN
        assert dai.started == 1573672677
        assert dai.forked is None
        assert dai.swapped_for is None
        assert dai.coingecko == 'dai'
        assert dai.cryptocompare is None
        assert dai.ethereum_address == '0x6B175474E89094C44Da98b954EedeAC495271d0F'
        assert dai.decimals == 8
        assert dai.protocol == 'maker'
        # make sure data is in both tables
        assert cursor.execute('SELECT COUNT(*) from ethereum_tokens WHERE address="0x6B175474E89094C44Da98b954EedeAC495271d0F";').fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F";').fetchone()[0] == 1  # noqa: E501

        dash = Asset('DASH')
        assert dash.identifier == 'DASH'
        assert dash.name == 'Dash'
        assert dash.symbol == 'DASH'
        assert dash.asset_type == AssetType.OWN_CHAIN
        assert dash.started == 1390095618
        assert dash.forked is None
        assert dash.swapped_for is None
        assert dash.coingecko == 'dash'
        assert dash.cryptocompare is None
        assert cursor.execute('SELECT COUNT(*) from common_asset_details WHERE asset_id="DASH";').fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="DASH";').fetchone()[0] == 1  # noqa: E501

        new_asset = Asset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''
        assert cursor.execute('SELECT COUNT(*) from common_asset_details WHERE asset_id="121-ada-FADS-as";').fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="121-ada-FADS-as";').fetchone()[0] == 1  # noqa: E501

        ctk = EthereumToken('0x1B175474E89094C44Da98b954EedeAC495271d0F')
        assert ctk.name == 'Conflicting token'
        assert ctk.symbol == 'CTK'
        assert ctk.asset_type == AssetType.ETHEREUM_TOKEN
        assert ctk.started == 1573672677
        assert ctk.forked is None
        assert ctk.swapped_for is None
        assert ctk.coingecko == 'ctk'
        assert ctk.cryptocompare is None
        assert ctk.ethereum_address == '0x1B175474E89094C44Da98b954EedeAC495271d0F'
        assert ctk.decimals == 18
        assert ctk.protocol is None
        assert cursor.execute('SELECT COUNT(*) from ethereum_tokens WHERE address="0x1B175474E89094C44Da98b954EedeAC495271d0F";').fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="_ceth_0x1B175474E89094C44Da98b954EedeAC495271d0F";').fetchone()[0] == 1  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_foreignkey_conflict(rotkehlchen_api_server, globaldb):
    """Test that when a conflict that's not solvable happens the entry is ignored

    One such case is when the update of an asset would violate a foreign key constraint.
    So we try to update the swapped_for to a non existing asset and make sure it's skipped.
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_1 = """INSERT INTO assets(identifier,type,name,symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("121-ada-FADS-as", "F","A name","SYMBOL",NULL, NULL,"", "", "121-ada-FADS-as");INSERT INTO common_asset_details(asset_id, forked) VALUES("121-ada-FADS-as", "BTC");
*
UPDATE assets SET swapped_for="_ceth_0xA8d35739EE92E69241A2Afd9F513d41021A07972" WHERE identifier="_ceth_0xa74476443119A942dE498590Fe1f2454d7D4aC0d";
INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES("0xa74476443119A942dE498590Fe1f2454d7D4aC0d", 18, NULL);INSERT INTO assets(identifier,type, name, symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("_ceth_0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "C", "Golem", "GNT", 1478810650, "_ceth_0xA8d35739EE92E69241A2Afd9F513d41021A07972", "golem", NULL, "0xa74476443119A942dE498590Fe1f2454d7D4aC0d");
    """  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999991,
        updates={"999999991": {
            "changes": 2,
            "min_schema_version": GLOBAL_DB_VERSION,
            "max_schema_version": GLOBAL_DB_VERSION,
        }},
        sql_actions={"999999991": update_1},
    )
    globaldb.add_setting_value(ASSETS_VERSION_KEY, 999999990)
    start_assets_num = len(globaldb.get_all_asset_data(mapping=False))
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
            result = assert_proper_response_with_result(response)
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
            result = assert_proper_response_with_result(
                response,
                message='Found conflicts during assets upgrade',
                status_code=HTTPStatus.CONFLICT,
            )

        # Make sure that nothing was committed
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999990
        assert len(globaldb.get_all_asset_data(mapping=False)) == start_assets_num
        with pytest.raises(UnknownAsset):
            Asset('121-ada-FADS-as')
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        # See that we get a conflict
        expected_result = [{
            'identifier': '_ceth_0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
            'local': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'ethereum token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': '_ceth_0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429',
                'ethereum_address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
            'remote': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'ethereum token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': '_ceth_0xA8d35739EE92E69241A2Afd9F513d41021A07972',
                'ethereum_address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
        }]
        assert result == expected_result

        # now try the update again but specify the conflicts resolution
        conflicts = {'_ceth_0xa74476443119A942dE498590Fe1f2454d7D4aC0d': 'remote'}
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
            result = assert_proper_response_with_result(
                response,
                message='',
                status_code=HTTPStatus.OK,
            )

        # check new asset was added and conflict was ignored with an error due to
        # inability to do anything with the missing swapped_for
        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999991
        gnt = EthereumToken('0xa74476443119A942dE498590Fe1f2454d7D4aC0d')
        assert gnt.identifier == strethaddress_to_identifier('0xa74476443119A942dE498590Fe1f2454d7D4aC0d')  # noqa: E501
        assert gnt.name == 'Golem'
        assert gnt.symbol == 'GNT'
        assert gnt.asset_type == AssetType.ETHEREUM_TOKEN
        assert gnt.started == 1478810650
        assert gnt.forked is None
        assert gnt.swapped_for == A_GLM.identifier
        assert gnt.coingecko == 'golem'
        assert gnt.cryptocompare is None
        assert gnt.ethereum_address == '0xa74476443119A942dE498590Fe1f2454d7D4aC0d'
        assert gnt.decimals == 18
        assert gnt.protocol is None

        new_asset = Asset('121-ada-FADS-as')
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
def test_update_from_early_clean_db(rotkehlchen_api_server, globaldb):
    """
    Test that if the asset upgrade happens from a very early DB that has had no assets
    version key set we still upgrade properly and set the assets version properly.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_1 = """INSERT INTO assets(identifier,type,name,symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("121-ada-FADS-as", "F","A name","SYMBOL",NULL, NULL,"", "", "121-ada-FADS-as");INSERT INTO common_asset_details(asset_id, forked) VALUES("121-ada-FADS-as", "BTC");
*
UPDATE assets SET swapped_for="_ceth_0xA8d35739EE92E69241A2Afd9F513d41021A07972" WHERE identifier="_ceth_0xa74476443119A942dE498590Fe1f2454d7D4aC0d";
INSERT INTO ethereum_tokens(address, decimals, protocol) VALUES("0xa74476443119A942dE498590Fe1f2454d7D4aC0d", 18, NULL);INSERT INTO assets(identifier,type, name, symbol,started, swapped_for, coingecko, cryptocompare, details_reference) VALUES("_ceth_0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "C", "Golem", "GNT", 1478810650, "_ceth_0xA8d35739EE92E69241A2Afd9F513d41021A07972", "golem", NULL, "0xa74476443119A942dE498590Fe1f2454d7D4aC0d");
    """  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=1,
        updates={"1": {
            "changes": 2,
            "min_schema_version": GLOBAL_DB_VERSION,
            "max_schema_version": GLOBAL_DB_VERSION,
        }},
        sql_actions={"1": update_1},
    )
    cursor = globaldb._conn.cursor()
    cursor.execute(f'DELETE FROM settings WHERE name="{ASSETS_VERSION_KEY}"')
    start_assets_num = len(globaldb.get_all_asset_data(mapping=False))
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
        )
        result = assert_proper_response_with_result(response)
        assert result['local'] == 0
        assert result['remote'] == 1
        assert result['new_changes'] == 2

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
        )
        result = assert_proper_response_with_result(
            response,
            message='Found conflicts during assets upgrade',
            status_code=HTTPStatus.CONFLICT,
        )

        # Make sure that nothing was committed
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 0
        assert len(globaldb.get_all_asset_data(mapping=False)) == start_assets_num
        with pytest.raises(UnknownAsset):
            Asset('121-ada-FADS-as')
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        # See that we get a conflict
        expected_result = [{
            'identifier': '_ceth_0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
            'local': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'ethereum token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': '_ceth_0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429',
                'ethereum_address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
            'remote': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'ethereum token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': '_ceth_0xA8d35739EE92E69241A2Afd9F513d41021A07972',
                'ethereum_address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
        }]
        assert result == expected_result

        # now try the update again but specify the conflicts resolution
        conflicts = {'_ceth_0xa74476443119A942dE498590Fe1f2454d7D4aC0d': 'remote'}
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'conflicts': conflicts},
        )
        result = assert_proper_response_with_result(
            response,
            message='',
            status_code=HTTPStatus.OK,
        )

        # check new asset was added and conflict was ignored with an error due to
        # inability to do anything with the missing swapped_for
        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 1
        gnt = EthereumToken('0xa74476443119A942dE498590Fe1f2454d7D4aC0d')
        assert gnt.identifier == strethaddress_to_identifier('0xa74476443119A942dE498590Fe1f2454d7D4aC0d')  # noqa: E501
        assert gnt.name == 'Golem'
        assert gnt.symbol == 'GNT'
        assert gnt.asset_type == AssetType.ETHEREUM_TOKEN
        assert gnt.started == 1478810650
        assert gnt.forked is None
        assert gnt.swapped_for == A_GLM.identifier
        assert gnt.coingecko == 'golem'
        assert gnt.cryptocompare is None
        assert gnt.ethereum_address == '0xa74476443119A942dE498590Fe1f2454d7D4aC0d'
        assert gnt.decimals == 18
        assert gnt.protocol is None

        new_asset = Asset('121-ada-FADS-as')
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
        assert f'Failed to resolve conflict for {gnt.identifier} in the DB during the v1 assets update. Skipping entry' in warnings[0]  # noqa: E501
