from copy import deepcopy
from http import HTTPStatus
from typing import Any, Dict, List

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.typing import AssetType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.typing import Location


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_adding_custom_assets(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for adding a custom asset works"""

    custom1 = {
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
        json=custom1,
    )
    result = assert_proper_response_with_result(response)
    custom1_id = result['identifier']

    data = globaldb.get_asset_data(identifier=custom1_id, form_with_incomplete_data=False)
    assert data.identifier == custom1_id
    assert data.asset_type == AssetType.OWN_CHAIN
    assert data.name == custom1['name']
    assert data.symbol == custom1['symbol']
    assert data.started == custom1['started']

    custom2 = {
        'asset_type': 'stellar token',
        'name': 'goo token',
        'symbol': 'GOO',
        'started': 6,
        'forked': custom1_id,
        'swapped_for': 'ETH',
        'coingecko': 'internet-computer',
        'cryptocompare': 'ICP',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom2,
    )
    result = assert_proper_response_with_result(response)
    custom2_id = result['identifier']

    data = globaldb.get_asset_data(identifier=custom2_id, form_with_incomplete_data=False)
    assert data.identifier == custom2_id
    assert data.asset_type == AssetType.STELLAR_TOKEN
    assert data.name == custom2['name']
    assert data.symbol == custom2['symbol']
    assert data.started == custom2['started']
    assert data.forked == custom2['forked']
    assert data.swapped_for == custom2['swapped_for']
    assert data.coingecko == custom2['coingecko']
    assert data.cryptocompare == custom2['cryptocompare']

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
    # try to add an ethereum token with the custom asset endpoint
    bad_asset = {
        'asset_type': 'ethereum token',
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
    expected_msg = 'Asset type ethereum token is not allowed in this endpoint'
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
    expected_msg = f'Given cryptocompare identifier {bad_id} isnt valid'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_editing_custom_assets(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for editing a custom asset works"""

    custom1 = {
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
        json=custom1,
    )
    result = assert_proper_response_with_result(response)
    custom1_id = result['identifier']

    data = globaldb.get_asset_data(identifier=custom1_id, form_with_incomplete_data=False)
    assert data.identifier == custom1_id
    assert data.asset_type == AssetType.OWN_CHAIN
    assert data.name == custom1['name']
    assert data.symbol == custom1['symbol']
    assert data.started == custom1['started']

    custom1_v2 = {
        'identifier': custom1_id,
        'asset_type': 'stellar token',
        'name': 'goo token',
        'symbol': 'GOO',
        'started': 6,
        'forked': custom1_id,
        'swapped_for': 'ETH',
        'coingecko': 'internet-computer',
        'cryptocompare': 'ICP',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom1_v2,
    )
    result = assert_proper_response_with_result(response)
    assert result is True

    data = globaldb.get_asset_data(identifier=custom1_id, form_with_incomplete_data=False)
    assert data.identifier == custom1_id
    assert data.asset_type == AssetType.STELLAR_TOKEN
    assert data.name == custom1_v2['name']
    assert data.symbol == custom1_v2['symbol']
    assert data.started == custom1_v2['started']
    assert data.forked == custom1_v2['forked']
    assert data.swapped_for == custom1_v2['swapped_for']
    assert data.coingecko == custom1_v2['coingecko']
    assert data.cryptocompare == custom1_v2['cryptocompare']

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
    # try to edit an ethereum token with the custom asset endpoint
    bad_asset = {
        'identifier': 'EUR',
        'asset_type': 'ethereum token',
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
    expected_msg = 'Asset type ethereum token is not allowed in this endpoint'
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
    expected_msg = f'Given cryptocompare identifier {bad_id} isnt valid'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_deleting_custom_assets(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for deleting a custom asset works"""

    custom1 = {
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
        json=custom1,
    )
    result = assert_proper_response_with_result(response)
    custom1_id = result['identifier']

    custom2 = {
        'asset_type': 'stellar token',
        'name': 'goo token',
        'symbol': 'GOO',
        'started': 6,
        'forked': custom1_id,
        'swapped_for': 'ETH',
        'coingecko': 'internet-computer',
        'cryptocompare': 'ICP',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom2,
    )
    result = assert_proper_response_with_result(response)
    custom2_id = result['identifier']

    custom3 = {
        'asset_type': 'own chain',
        'name': 'boo token',
        'symbol': 'BOO',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom3,
    )
    result = assert_proper_response_with_result(response)
    custom3_id = result['identifier']

    # Delete custom 3 and assert it works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom3_id},
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    assert globaldb.get_asset_data(identifier=custom3_id, form_with_incomplete_data=False) is None

    # Try to delete custom1 but make sure it fails. It's used by custom2
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom1_id},
    )
    expected_msg = 'Tried to delete asset with name "foo token" and symbol "FOO" but its deletion would violate a constraint so deletion failed'  # noqa: E501
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # Delete custom 2 and assert it works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom2_id},
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    assert globaldb.get_asset_data(identifier=custom2_id, form_with_incomplete_data=False) is None

    # now custom 1 should be deletable
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom1_id},
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    assert globaldb.get_asset_data(identifier=custom1_id, form_with_incomplete_data=False) is None

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
def test_custom_asset_delete_guard(rotkehlchen_api_server):
    """Test that deleting an owned asset is guarded against"""
    user_db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    custom1 = {
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
        json=custom1,
    )
    result = assert_proper_response_with_result(response)
    custom1_id = result['identifier']
    user_db.add_manually_tracked_balances([ManuallyTrackedBalance(
        asset=Asset(custom1_id),
        label='manual1',
        amount=FVal(1),
        location=Location.EXTERNAL,
        tags=None,
    )])
    # Try to delete the asset and see it fails because a user owns it
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom1_id},
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
    assert result == [str(x) for x in AssetType]
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
    custom1 = {
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
        json=custom1,
    )
    result = assert_proper_response_with_result(response)
    custom1_id = result['identifier']

    if only_in_globaldb:
        cursor.execute('DELETE FROM assets where identifier=?', (custom1_id,))

    balances: List[Dict[str, Any]] = [{
        'asset': custom1_id,
        'label': 'ICP account',
        'amount': '50.315',
        'location': 'blockchain',
    }]
    expected_balances = deepcopy(balances)
    expected_balances[0]['usd_value'] = str(FVal(balances[0]['amount']) * FVal('1.5'))
    expected_balances[0]['tags'] = None

    if not only_in_globaldb:
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'manuallytrackedbalancesresource',
            ), json={'async_query': False, 'balances': balances},
        )
        assert_proper_response_with_result(response)

    # before the replacement. Check that we got a globaldb entry in owned assets
    global_cursor = globaldb._conn.cursor()
    if not only_in_globaldb:
        assert global_cursor.execute(
            'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (custom1_id,),
        ).fetchone()[0] == 1
        # check the custom asset is in user db
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (custom1_id,),
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
            (custom1_id,),
        ).fetchone()[0] == 1

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': custom1_id, 'target_asset': 'ICP'},
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
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (custom1_id,),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', ('ICP',),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) from manually_tracked_balances WHERE asset=?;',
            (custom1_id,),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) from manually_tracked_balances WHERE asset=?;',
            ('ICP',),
        ).fetchone()[0] == 1

    # check the previous asset is not in globaldb owned assets
    assert global_cursor.execute(
        'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (custom1_id,),
    ).fetchone()[0] == 0
    # check the previous asset is not in globaldb
    assert global_cursor.execute(
        'SELECT COUNT(*) FROM assets WHERE identifier=?', (custom1_id,),
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
        'asset': 'ICP',
        'label': 'forgotten balance',
        'amount': '1',
        'usd_value': '1.5',
        'tags': None,
        'location': 'external',
    }]
    # check the previous asset is not in globaldb owned assets
    global_cursor = globaldb._conn.cursor()
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
    global_cursor = globaldb._conn.cursor()

    def assert_db() -> None:
        assert global_cursor.execute(
            'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (glm_id,),
        ).fetchone()[0] == 1
        assert global_cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE swapped_for=?', (glm_id,),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (glm_id,),
        ).fetchone()[0] == 1

    assert_db()
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': glm_id, 'target_asset': 'ICP'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to delete ethereum token with address',
        status_code=HTTPStatus.CONFLICT,
    )
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
