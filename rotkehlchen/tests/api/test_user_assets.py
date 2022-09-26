import json
import tempfile
from copy import deepcopy
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict, List
from zipfile import ZipFile

import pytest
import requests

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.misc import ASSET_TYPES_EXCLUDED_FOR_USERS, ONE
from rotkehlchen.constants.resolver import (
    ChainID,
    ethaddress_to_identifier,
    strethaddress_to_identifier,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.types import EvmTokenKind, Location


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_add_user_assets(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for adding a user asset works"""

    user_asset1 = {
        'asset_type': 'own chain',
        'name': 'foo token',
        'symbol': 'FOO',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset1,
    )
    result = assert_proper_response_with_result(response)
    user_asset1_id = result['identifier']

    data = globaldb.get_asset_data(identifier=user_asset1_id, form_with_incomplete_data=False)
    assert data.identifier == user_asset1_id
    assert data.asset_type == AssetType.OWN_CHAIN
    assert data.name == user_asset1['name']
    assert data.symbol == user_asset1['symbol']
    assert data.started == user_asset1['started']

    user_asset2 = {
        'asset_type': 'stellar token',
        'name': 'goo token',
        'symbol': 'GOO',
        'started': 6,
        'forked': user_asset1_id,
        'swapped_for': 'ETH',
        'coingecko': 'internet-computer',
        'cryptocompare': 'ICP',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset2,
    )
    result = assert_proper_response_with_result(response)
    user_asset2_id = result['identifier']

    data = globaldb.get_asset_data(identifier=user_asset2_id, form_with_incomplete_data=False)
    assert data.identifier == user_asset2_id
    assert data.asset_type == AssetType.STELLAR_TOKEN
    assert data.name == user_asset2['name']
    assert data.symbol == user_asset2['symbol']
    assert data.started == user_asset2['started']
    assert data.forked == user_asset2['forked']
    assert data.swapped_for == user_asset2['swapped_for']
    assert data.coingecko == user_asset2['coingecko']
    assert data.cryptocompare == user_asset2['cryptocompare']

    # try to add a token type/name/symbol combo that exists
    bad_asset = {
        'asset_type': 'fiat',
        'name': 'Euro',
        'symbol': 'EUR',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Failed to add fiat Euro since it already exists. Existing ids: EUR'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )
    # try to add an ethereum token with the user asset endpoint
    bad_asset = {
        'asset_type': 'evm token',
        'name': 'Euro',
        'symbol': 'EUR',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Asset type evm token is not allowed in this endpoint'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # try to add non existing forked and swapped for
    bad_asset = {
        'asset_type': 'omni token',
        'name': 'Euro',
        'symbol': 'EUR',
        'forked': 'dsadsadsadasd',
        'swapped_for': 'asdsadsad',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Unknown asset'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # try to add invalid coingecko
    bad_id = 'dsadsad'
    bad_asset = {
        'asset_type': 'omni token',
        'name': 'Euro',
        'symbol': 'EUR',
        'coingecko': bad_id,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = f'Given coingecko identifier {bad_id} is not valid'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # try to add invalid cryptocompare
    bad_id = 'dsadsad'
    bad_asset = {
        'asset_type': 'omni token',
        'name': 'Euro',
        'symbol': 'EUR',
        'cryptocompare': bad_id,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = f'Given cryptocompare identifier {bad_id} is not valid'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_editing_user_assets(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for editing user assets works"""

    user_asset1 = {
        'asset_type': 'own chain',
        'name': 'foo token',
        'symbol': 'FOO',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset1,
    )
    result = assert_proper_response_with_result(response)
    user_asset1_id = result['identifier']

    data = globaldb.get_asset_data(identifier=user_asset1_id, form_with_incomplete_data=False)
    assert data.identifier == user_asset1_id
    assert data.asset_type == AssetType.OWN_CHAIN
    assert data.name == user_asset1['name']
    assert data.symbol == user_asset1['symbol']
    assert data.started == user_asset1['started']

    user_asset1_v2 = {
        'identifier': user_asset1_id,
        'asset_type': 'stellar token',
        'name': 'goo token',
        'symbol': 'GOO',
        'started': 6,
        'forked': user_asset1_id,
        'swapped_for': 'ETH',
        'coingecko': 'internet-computer',
        'cryptocompare': 'ICP',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset1_v2,
    )
    result = assert_proper_response_with_result(response)
    assert result is True

    data = globaldb.get_asset_data(identifier=user_asset1_id, form_with_incomplete_data=False)
    assert data.identifier == user_asset1_id
    assert data.asset_type == AssetType.STELLAR_TOKEN
    assert data.name == user_asset1_v2['name']
    assert data.symbol == user_asset1_v2['symbol']
    assert data.started == user_asset1_v2['started']
    assert data.forked == user_asset1_v2['forked']
    assert data.swapped_for == user_asset1_v2['swapped_for']
    assert data.coingecko == user_asset1_v2['coingecko']
    assert data.cryptocompare == user_asset1_v2['cryptocompare']

    # try to edit an asset with a non-existing identifier
    bad_asset = {
        'identifier': 'notexisting',
        'asset_type': 'own chain',
        'name': 'Euro',
        'symbol': 'EUR',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Tried to edit non existing asset with identifier notexisting'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )
    # try to edit an ethereum token with the user asset endpoint
    bad_asset = {
        'identifier': 'EUR',
        'asset_type': 'evm token',
        'name': 'ethereum Euro',
        'symbol': 'EUR',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Asset type evm token is not allowed in this endpoint'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # try to edit non existing forked and swapped for
    bad_asset = {
        'identifier': 'EUR',
        'asset_type': 'omni token',
        'name': 'Euro',
        'symbol': 'EUR',
        'forked': 'dsadsadsadasd',
        'swapped_for': 'asdsadsad',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Unknown asset'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # try to edit invalid coingecko
    bad_id = 'dsadsad'
    bad_asset = {
        'identifier': 'EUR',
        'asset_type': 'omni token',
        'name': 'Euro',
        'symbol': 'EUR',
        'coingecko': bad_id,
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = f'Given coingecko identifier {bad_id} is not valid'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # try to add invalid cryptocompare
    bad_id = 'dsadsad'
    bad_asset = {
        'identifier': 'EUR',
        'asset_type': 'omni token',
        'name': 'Euro',
        'symbol': 'EUR',
        'cryptocompare': bad_id,
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = f'Given cryptocompare identifier {bad_id} is not valid'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_deleting_user_assets(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for deleting a user asset works"""

    user_asset1 = {
        'asset_type': 'own chain',
        'name': 'foo token',
        'symbol': 'FOO',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset1,
    )
    result = assert_proper_response_with_result(response)
    user_asset1_id = result['identifier']

    user_asset2 = {
        'asset_type': 'stellar token',
        'name': 'goo token',
        'symbol': 'GOO',
        'started': 6,
        'forked': user_asset1_id,
        'swapped_for': 'ETH',
        'coingecko': 'internet-computer',
        'cryptocompare': 'ICP',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset2,
    )
    result = assert_proper_response_with_result(response)
    user_asset2_id = result['identifier']

    user_asset3 = {
        'asset_type': 'own chain',
        'name': 'boo token',
        'symbol': 'BOO',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset3,
    )
    result = assert_proper_response_with_result(response)
    user_asset3_id = result['identifier']

    # Delete user asset 3 and assert it works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': user_asset3_id},
    )
    assert_proper_response(response)
    assert globaldb.get_asset_data(identifier=user_asset3_id, form_with_incomplete_data=False) is None  # noqa: E501

    # Delete user_asset1 and assert it works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': user_asset1_id},
    )
    assert_proper_response(response)
    assert globaldb.get_asset_data(identifier=user_asset1_id, form_with_incomplete_data=False) is None  # noqa: E501
    # Also check that `forked` was updated
    assert globaldb.get_asset_data(identifier=user_asset2_id, form_with_incomplete_data=False).forked is None  # noqa: E501

    # Delete user asset 2 and assert it works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': user_asset2_id},
    )
    assert_proper_response(response)
    assert globaldb.get_asset_data(identifier=user_asset2_id, form_with_incomplete_data=False) is None  # noqa: E501

    # Make sure that deleting unknown asset is detected
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': 'notexisting'},
    )
    expected_msg = 'Tried to delete asset with identifier notexisting but it was not found in the DB'  # noqa: E501
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_user_asset_delete_guard(rotkehlchen_api_server):
    """Test that deleting an owned asset is guarded against"""
    user_db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    user_asset1 = {
        'asset_type': 'own chain',
        'name': 'foo token',
        'symbol': 'FOO',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset1,
    )
    result = assert_proper_response_with_result(response)
    user_asset1_id = result['identifier']
    with user_db.user_write() as cursor:
        user_db.add_manually_tracked_balances(cursor, [ManuallyTrackedBalance(
            id=-1,
            asset=Asset(user_asset1_id),
            label='manual1',
            amount=ONE,
            location=Location.EXTERNAL,
            tags=None,
            balance_type=BalanceType.ASSET,
        )])

    # Try to delete the asset and see it fails because a user owns it
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': user_asset1_id},
    )
    expected_msg = 'Failed to delete asset with id'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_query_asset_types(rotkehlchen_api_server):
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'assetstypesresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == [str(x) for x in AssetType if x not in ASSET_TYPES_EXCLUDED_FOR_USERS]
    assert all(isinstance(AssetType.deserialize(x), AssetType) for x in result)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('only_in_globaldb', [True, False])
def test_replace_asset(rotkehlchen_api_server, globaldb, only_in_globaldb):
    """Test that the endpoint for replacing an asset identifier works

    Test for both an asset owned by the user and not (the only_in_globaldb case)
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    cursor = rotki.data.db.conn.cursor()
    user_asset1 = {
        'asset_type': 'own chain',
        'name': 'Dfinity token',
        'symbol': 'ICP',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset1,
    )
    result = assert_proper_response_with_result(response)
    user_asset1_id = result['identifier']

    if only_in_globaldb:
        cursor.execute('DELETE FROM assets where identifier=?', (user_asset1_id,))

    balances: List[Dict[str, Any]] = [{
        'asset': user_asset1_id,
        'label': 'ICP account',
        'amount': '50.315',
        'location': 'blockchain',
        'balance_type': 'asset',
    }]
    expected_balances = deepcopy(balances)
    expected_balances[0]['usd_value'] = str(FVal(balances[0]['amount']) * FVal('1.5'))
    expected_balances[0]['tags'] = None
    expected_balances[0]['id'] = 1

    if not only_in_globaldb:
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'manuallytrackedbalancesresource',
            ), json={'async_query': False, 'balances': balances},
        )
        assert_proper_response_with_result(response)

    # before the replacement. Check that we got a globaldb entry in owned assets
    global_cursor = globaldb.conn.cursor()
    if not only_in_globaldb:
        assert global_cursor.execute(
            'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (user_asset1_id,),
        ).fetchone()[0] == 1
        # check the user asset asset is in user db
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (user_asset1_id,),
        ).fetchone()[0] == 1
        # Check that the manual balance is returned
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'manuallytrackedbalancesresource',
            ), json={'async_query': False},
        )
        result = assert_proper_response_with_result(response)
        assert result['balances'] == expected_balances
        assert cursor.execute(
            'SELECT COUNT(*) from manually_tracked_balances WHERE asset=?;',
            (user_asset1_id,),
        ).fetchone()[0] == 1

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': user_asset1_id, 'target_asset': 'ICP'},
    )
    assert_simple_ok_response(response)

    # after the replacement. Check that the manual balance is changed
    if not only_in_globaldb:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'manuallytrackedbalancesresource',
            ), json={'async_query': False},
        )
        result = assert_proper_response_with_result(response)
        expected_balances[0]['asset'] = 'ICP'
        assert result['balances'] == expected_balances
        # check the previous asset is not in userdb anymore
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (user_asset1_id,),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', ('ICP',),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) from manually_tracked_balances WHERE asset=?;',
            (user_asset1_id,),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) from manually_tracked_balances WHERE asset=?;',
            ('ICP',),
        ).fetchone()[0] == 1

    # check the previous asset is not in globaldb owned assets
    assert global_cursor.execute(
        'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (user_asset1_id,),
    ).fetchone()[0] == 0
    # check the previous asset is not in globaldb
    assert global_cursor.execute(
        'SELECT COUNT(*) FROM assets WHERE identifier=?', (user_asset1_id,),
    ).fetchone()[0] == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_replace_asset_not_in_globaldb(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for replacing an asset identifier works even if
    the source asset identifier is not in the global DB"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Emulate some custom state that can be reached if somehow you end up with a user
    # DB asset that is not in the global DB
    unknown_id = 'foo-boo-goo-doo'
    cursor = rotki.data.db.conn.cursor()
    cursor.execute('INSERT INTO assets VALUES(?)', (unknown_id,))
    cursor.execute(
        'INSERT INTO manually_tracked_balances(asset, label, amount, location) '
        'VALUES (?, ?, ?, ?)',
        (unknown_id, 'forgotten balance', '1', 'A'),
    )
    assert cursor.execute(
        'SELECT COUNT(*) FROM assets WHERE identifier=?', (unknown_id,),
    ).fetchone()[0] == 1
    # Check that the manual balance is there -- can't query normally due to unknown asset
    assert cursor.execute(
        'SELECT COUNT(*) FROM manually_tracked_balances WHERE asset=?', (unknown_id,),
    ).fetchone()[0] == 1

    # now do the replacement
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': unknown_id, 'target_asset': 'ICP'},
    )
    assert_simple_ok_response(response)

    # after the replacement. Check that the manual balance is changed an is now queriable
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': False},
    )
    result = assert_proper_response_with_result(response)
    assert result['balances'] == [{
        'id': 1,
        'asset': 'ICP',
        'label': 'forgotten balance',
        'amount': '1',
        'usd_value': '1.5',
        'tags': None,
        'location': 'external',
        'balance_type': 'asset',
    }]
    # check the previous asset is not in globaldb owned assets
    global_cursor = globaldb.conn.cursor()
    assert global_cursor.execute(
        'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (unknown_id,),
    ).fetchone()[0] == 0
    # check the previous asset is not in globaldb
    assert global_cursor.execute(
        'SELECT COUNT(*) FROM assets WHERE identifier=?', (unknown_id,),
    ).fetchone()[0] == 0
    # check the previous asset is not in userdb anymore
    assert cursor.execute(
        'SELECT COUNT(*) FROM assets WHERE identifier=?', (unknown_id,),
    ).fetchone()[0] == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_replace_asset_edge_cases(rotkehlchen_api_server, globaldb):
    """Test that the edge cases/errors are treated properly in the replace assets endpoint"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    cursor = rotki.data.db.conn.cursor()

    # Test that completely unknown source asset returns error
    notexisting_id = 'boo-boo-ga-ga'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': notexisting_id, 'target_asset': 'ICP'},
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Unknown asset {notexisting_id} provided',
        status_code=HTTPStatus.CONFLICT,
    )

    # Test that trying to replace an asset that's used as a foreign key elsewhere in
    # the global DB does not work, error is returned and no changes happen
    # in the global DB and in the user DB
    glm_id = strethaddress_to_identifier('0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429')
    balances: List[Dict[str, Any]] = [{
        'asset': glm_id,
        'label': 'ICP account',
        'amount': '50.315',
        'location': 'blockchain',
    }]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': False, 'balances': balances},
    )
    assert_proper_response_with_result(response)
    global_cursor = globaldb.conn.cursor()

    def assert_db() -> None:
        assert global_cursor.execute(
            'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (glm_id,),
        ).fetchone()[0] == 1
        assert global_cursor.execute(
            'SELECT COUNT(*) FROM common_asset_details WHERE swapped_for=?', (glm_id,),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (glm_id,),
        ).fetchone()[0] == 1

    assert_db()

    # Test non-string source identifier
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': 55.1, 'target_asset': 'ICP'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test unknown target asset
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': 'ETH', 'target_asset': 'bobobobobo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset bobobobobo provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test invalid target asset
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': 'ETH', 'target_asset': 55},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': glm_id, 'target_asset': 'ICP'},
    )
    assert_proper_response(response)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('with_custom_path', [False, True])
def test_exporting_user_assets_list(rotkehlchen_api_server, globaldb, with_custom_path):
    """Test that the endpoint for exporting user assets works correctly"""
    eth_address = make_ethereum_address()
    identifier = ethaddress_to_identifier(eth_address)
    globaldb.add_asset(
        asset_id=identifier,
        asset_type=AssetType.EVM_TOKEN,
        data=EvmToken.initialize(
            address=eth_address,
            chain=ChainID.ETHEREUM,
            token_kind=EvmTokenKind.ERC20,
            decimals=18,
            name='yabirtoken',
            symbol='YAB',
            coingecko='YAB',
            cryptocompare='YAB',
        ),
    )
    with tempfile.TemporaryDirectory() as path:
        if with_custom_path:
            response = requests.put(
                api_url_for(
                    rotkehlchen_api_server,
                    'userassetsresource',
                ), json={'action': 'download', 'destination': path},
            )
        else:
            response = requests.put(
                api_url_for(
                    rotkehlchen_api_server,
                    'userassetsresource',
                ), json={'action': 'download'},
            )

        if with_custom_path:
            result = assert_proper_response_with_result(response)
            if with_custom_path:
                assert path in result['file']
            zip_file = ZipFile(result['file'])
            data = json.loads(zip_file.read('assets.json'))
            assert int(data['version']) == GLOBAL_DB_VERSION
            assert len(data['assets']) == 1
            assert data['assets'][0] == {
                'identifier': identifier,
                'name': 'yabirtoken',
                'chain': 'ethereum',
                'asset_type': 'evm token',
                'decimals': 18,
                'symbol': 'YAB',
                'asset_type': 'evm token',
                'started': None,
                'forked': None,
                'swapped_for': None,
                'cryptocompare': 'YAB',
                'coingecko': 'YAB',
                'protocol': None,
                'token_kind': 'erc20',
                'underlying_tokens': None,
                'address': eth_address,
            }
        else:
            assert response.status_code == HTTPStatus.OK
            assert response.headers['Content-Type'] == 'application/zip'

        # try to download again to see if the database is properly detached
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'userassetsresource',
            ), json={'action': 'download', 'destination': path},
        )
        result = assert_proper_response_with_result(response)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('method', ['post', 'put'])
@pytest.mark.parametrize('file_type', ['zip', 'json'])
def test_importing_user_assets_list(rotkehlchen_api_server, method, file_type):
    """Test that the endpoint for importing user assets works correctly"""
    dir_path = Path(__file__).resolve().parent.parent
    if file_type == 'zip':
        filepath = dir_path / 'data' / 'exported_assets.zip'
    else:
        filepath = dir_path / 'data' / 'exported_assets.json'

    if method == 'put':
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'userassetsresource',
            ), json={'action': 'upload', 'file': str(filepath)},
        )
    else:
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'userassetsresource',
            ), json={'action': 'upload'},
            files={'file': open(filepath, 'rb')},
        )

    assert_simple_ok_response(response)
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    errors = rotki.msg_aggregator.consume_errors()
    warnings = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    assert_proper_response_with_result(response)
    stinch = EvmToken('eip155:1/erc20:0xA0446D8804611944F1B527eCD37d7dcbE442caba')
    assert stinch.symbol == 'st1INCH'
    assert len(stinch.underlying_tokens) == 1
    assert stinch.decimals == 18
