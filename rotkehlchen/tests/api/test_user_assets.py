import json
import random
import tempfile
from copy import deepcopy
from http import HTTPStatus
from pathlib import Path
from zipfile import ZipFile

import pytest
import requests

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.api.server import APIServer
from rotkehlchen.assets.asset import Asset, CustomAsset, EvmToken
from rotkehlchen.assets.types import ASSET_TYPES_EXCLUDED_FOR_USERS, AssetType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_BCH, A_BTC, A_DAI, A_DOT, A_EUR, A_USDC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.resolver import (
    ChainID,
    ethaddress_to_identifier,
    evm_address_to_identifier,
    strethaddress_to_identifier,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION, GlobalDBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import Location, TokenKind


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('coingecko_cache_coinlist', [{
    'internet-computer': {'symbol': 'ICP', 'name': 'Internet computer'},
}])
@pytest.mark.parametrize('cryptocompare_cache_coinlist', [{'ICP': {}}])
def test_add_user_assets(
        rotkehlchen_api_server: APIServer,
        globaldb: GlobalDBHandler,
        cache_coinlist: list[dict[str, dict]],
) -> None:  # pylint: disable=unused-argument
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
    result = assert_proper_sync_response_with_result(response)
    user_asset1_id = result['identifier']

    data = globaldb.get_asset_data(identifier=user_asset1_id, form_with_incomplete_data=False)
    assert data is not None
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
    result = assert_proper_sync_response_with_result(response)
    user_asset2_id = result['identifier']

    data = globaldb.get_asset_data(identifier=user_asset2_id, form_with_incomplete_data=False)
    assert data is not None
    assert data.identifier == user_asset2_id
    assert data.asset_type == AssetType.STELLAR_TOKEN
    assert data.name == user_asset2['name']
    assert data.symbol == user_asset2['symbol']
    assert data.started == user_asset2['started']
    assert data.forked == user_asset2['forked']
    assert data.swapped_for == user_asset2['swapped_for']
    assert data.coingecko == user_asset2['coingecko']
    assert data.cryptocompare == user_asset2['cryptocompare']

    # Add a fiat asset with the user asset endpoint
    fiat_asset_data = {
        'identifier': 'new-fiat-asset',
        'asset_type': 'fiat',
        'name': 'Awesome new fiat asset',
        'symbol': 'NEWFIAT',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=fiat_asset_data,
    )
    assert_proper_response(response)
    resolved_eur = Asset('new-fiat-asset').resolve_to_fiat_asset()
    assert resolved_eur.name == 'Awesome new fiat asset'
    assert resolved_eur.symbol == 'NEWFIAT'

    # Add an evm token with the user asset endpoint
    new_evm_token_address = make_evm_address()
    new_evm_token_data = {
        'asset_type': 'evm token',
        'name': 'New ERC20 token',
        'symbol': 'NEWTOKEN',
        'token_kind': 'ERC20',
        'address': new_evm_token_address,
        'decimals': 18,
        'evm_chain': 'ethereum',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=new_evm_token_data,
    )
    new_token = EvmToken(evm_address_to_identifier(
        address=new_evm_token_address,
        chain_id=ChainID.ETHEREUM,
        token_type=TokenKind.ERC20,
    ))
    assert new_token.name == 'New ERC20 token'
    assert new_token.symbol == 'NEWTOKEN'

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
@pytest.mark.parametrize('coingecko_cache_coinlist', [{
    'internet-computer': {'symbol': 'ICP', 'name': 'Internet computer'},
}])
@pytest.mark.parametrize('cryptocompare_cache_coinlist', [{'ICP': {}}])
def test_editing_user_assets(
        rotkehlchen_api_server: APIServer,
        globaldb: GlobalDBHandler,
        cache_coinlist: list[dict[str, dict]],
) -> None:  # pylint: disable=unused-argument
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
    result = assert_proper_sync_response_with_result(response)
    user_asset1_id = result['identifier']

    data = globaldb.get_asset_data(identifier=user_asset1_id, form_with_incomplete_data=False)
    assert data is not None
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
    result = assert_proper_sync_response_with_result(response)
    assert result is True

    data = globaldb.get_asset_data(identifier=user_asset1_id, form_with_incomplete_data=False)
    assert data is not None
    assert data.identifier == user_asset1_id
    assert data.asset_type == AssetType.STELLAR_TOKEN
    assert data.name == user_asset1_v2['name']
    assert data.symbol == user_asset1_v2['symbol']
    assert data.started == user_asset1_v2['started']
    assert data.forked == user_asset1_v2['forked']
    assert data.swapped_for == user_asset1_v2['swapped_for']
    assert data.coingecko == user_asset1_v2['coingecko']
    assert data.cryptocompare == user_asset1_v2['cryptocompare']

    # Edit an evm token with the user asset endpoint
    evm_token_data = {
        'asset_type': 'evm token',
        'name': 'Edited DAI',
        'symbol': 'NEWDAI',
        'token_kind': 'ERC20',
        'address': '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
        'decimals': 18,
        'evm_chain': 'ethereum',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=evm_token_data,
    )
    assert_proper_response(response)
    resolved_dai = A_DAI.resolve_to_evm_token()
    assert resolved_dai.name == 'Edited DAI'
    assert resolved_dai.symbol == 'NEWDAI'

    # Edit a fiat asset with the user asset endpoint
    fiat_asset_data = {
        'identifier': 'EUR',
        'asset_type': 'fiat',
        'name': 'Edited EUR',
        'symbol': 'NEWEUR',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=fiat_asset_data,
    )
    assert_proper_response(response)
    resolved_eur = A_EUR.resolve_to_fiat_asset()
    assert resolved_eur.name == 'Edited EUR'
    assert resolved_eur.symbol == 'NEWEUR'

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
@pytest.mark.parametrize('coingecko_cache_coinlist', [{
    'internet-computer': {'symbol': 'ICP', 'name': 'Internet computer'},
}])
@pytest.mark.parametrize('cryptocompare_cache_coinlist', [{'ICP': {}}])
def test_deleting_user_assets(
        rotkehlchen_api_server: APIServer,
        globaldb: GlobalDBHandler,
        cache_coinlist: list[dict[str, dict]],
) -> None:  # pylint: disable=unused-argument
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
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

    assert (asset_data := globaldb.get_asset_data(identifier=user_asset2_id, form_with_incomplete_data=False)) is not None  # noqa: E501
    assert asset_data.forked is None

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
def test_user_asset_delete_guard(rotkehlchen_api_server: APIServer) -> None:
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
    result = assert_proper_sync_response_with_result(response)
    user_asset1_id = result['identifier']
    with user_db.user_write() as cursor:
        user_db.add_manually_tracked_balances(cursor, [ManuallyTrackedBalance(
            identifier=-1,
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
def test_query_asset_types(rotkehlchen_api_server: APIServer) -> None:
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'assetstypesresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == [str(x) for x in AssetType if x not in ASSET_TYPES_EXCLUDED_FOR_USERS]
    assert all(isinstance(AssetType.deserialize(x), AssetType) for x in result)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('only_in_globaldb', [True, False])
def test_replace_asset(
        rotkehlchen_api_server: APIServer,
        globaldb: GlobalDBHandler,
        only_in_globaldb: bool,
) -> None:
    """Test that the endpoint for replacing an asset identifier works

    Test for both an asset owned by the user and not (the only_in_globaldb case)
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
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
    result = assert_proper_sync_response_with_result(response)
    user_asset1_id = result['identifier']

    if only_in_globaldb:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            write_cursor.execute('DELETE FROM assets where identifier=?', (user_asset1_id,))

    balances = [{
        'asset': user_asset1_id,
        'label': 'ICP account',
        'amount': '50.315',
        'location': 'blockchain',
        'balance_type': 'asset',
    }]
    expected_balances = deepcopy(balances)
    expected_balances[0]['usd_value'] = str(FVal(balances[0]['amount']) * FVal('1.5'))
    expected_balances[0]['tags'] = None
    expected_balances[0]['identifier'] = 1
    expected_api_balances = expected_balances

    if not only_in_globaldb:
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'manuallytrackedbalancesresource',
            ), json={'async_query': False, 'balances': balances},
        )
        assert_proper_sync_response_with_result(response)

    # before the replacement. Check that we got a globaldb entry in owned assets
    if not only_in_globaldb:
        with globaldb.conn.read_ctx() as global_cursor:
            assert global_cursor.execute(
                'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (user_asset1_id,),
            ).fetchone()[0] == 1
        # check the user asset is in user db
        with rotki.data.db.conn.read_ctx() as cursor:
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
        result = assert_proper_sync_response_with_result(response)
        assert len(expected_balances) == 1
        expected_api_balances = [{**expected_balances[0], 'asset_is_missing': False}]
        assert result['balances'] == expected_api_balances
        with rotki.data.db.conn.read_ctx() as cursor:
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

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'assetsreplaceresource',
        ),
        json={'source_identifier': 'etc', 'target_asset': 'ETC'},
    )
    assert_error_response(response)  # same identifier with different casing, not allowed

    # after the replacement. Check that the manual balance is changed
    if not only_in_globaldb:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'manuallytrackedbalancesresource',
            ), json={'async_query': False},
        )
        result = assert_proper_sync_response_with_result(response)
        expected_api_balances[0]['asset'] = 'ICP'
        assert result['balances'] == expected_api_balances
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
def test_replace_asset_not_in_globaldb(
        rotkehlchen_api_server: APIServer,
        globaldb: GlobalDBHandler,
) -> None:
    """Test that the endpoint for replacing an asset identifier works even if
    the source asset identifier is not in the global DB"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Emulate some custom state that can be reached if somehow you end up with a user
    # DB asset that is not in the global DB
    unknown_id = 'foo-boo-goo-doo'
    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO assets VALUES(?)', (unknown_id,))
        write_cursor.execute(
            'INSERT INTO manually_tracked_balances(asset, label, amount, location) '
            'VALUES (?, ?, ?, ?)',
            (unknown_id, 'forgotten balance', '1', 'A'),
        )
    with rotki.data.db.conn.read_ctx() as cursor:
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

    # after the replacement. Check that the manual balance is changed and is now queriable
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': False},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['balances'] == [{
        'identifier': 1,
        'asset': 'ICP',
        'label': 'forgotten balance',
        'amount': '1',
        'usd_value': '1.5',
        'tags': None,
        'location': 'external',
        'balance_type': 'asset',
        'asset_is_missing': False,
    }]
    # check the previous asset is not in globaldb owned assets
    with globaldb.conn.read_ctx() as global_cursor:
        assert global_cursor.execute(
            'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (unknown_id,),
        ).fetchone()[0] == 0
        # check the previous asset is not in globaldb
        assert global_cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (unknown_id,),
        ).fetchone()[0] == 0
    # check the previous asset is not in userdb anymore
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (unknown_id,),
        ).fetchone()[0] == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_replace_asset_edge_cases(
        rotkehlchen_api_server: APIServer,
        globaldb: GlobalDBHandler,
) -> None:
    """Test that the edge cases/errors are treated properly in the replace assets endpoint"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

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

    # add a user asset
    user_asset = {
        'asset_type': 'own chain',
        'name': 'My token',
        'symbol': 'DYM',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=user_asset,
    )
    result = assert_proper_sync_response_with_result(response)
    user_asset_id = result['identifier']

    # Test that trying to replace an asset that's used as a foreign key elsewhere in
    # the global DB does not work, error is returned and no changes happen
    # in the global DB and in the user DB
    glm_id = strethaddress_to_identifier('0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429')
    balances = [{
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
    assert_proper_sync_response_with_result(response)

    def assert_db() -> None:
        with globaldb.conn.read_ctx() as global_cursor:
            assert global_cursor.execute(
                'SELECT COUNT(*) FROM user_owned_assets WHERE asset_id=?', (glm_id,),
            ).fetchone()[0] == 1
            assert global_cursor.execute(
                'SELECT COUNT(*) FROM common_asset_details WHERE swapped_for=?', (glm_id,),
            ).fetchone()[0] == 1
        with rotki.data.db.conn.read_ctx() as cursor:
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

    # try to merge combinations of EVM tokens/other assets. When the source is a evm token it
    # should fail to avoid users from breaking assets in history events and other places
    for asset_a, asset_b, maybe_error in (
        (A_DAI.identifier, A_USDC.identifier, "Can't replace an evm token"),  # evm -> evm
        (A_DAI.identifier, A_BTC.identifier, "Can't replace an evm token"),  # evm -> normal
        (A_DOT.identifier, A_USDC.identifier, ''),  # normal -> evm
        (A_BTC.identifier, A_BCH.identifier, ''),  # normal -> normal
        (user_asset_id, user_asset_id, "Can't merge the same asset to itself"),  # Same user asset as source and target  # noqa: E501
        (A_BCH.identifier, A_BCH.identifier, "Can't merge the same asset to itself"),  # Same asset as source and target  # noqa: E501
    ):
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'assetsreplaceresource',
            ),
            json={'source_identifier': asset_a, 'target_asset': asset_b},
        )
        if not maybe_error:
            assert_proper_response(response)
        else:
            assert_error_response(
                response=response,
                contained_in_msg=maybe_error,
                status_code=HTTPStatus.BAD_REQUEST,
            )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('with_custom_path', [False, True])
def test_exporting_user_assets_list(
        rotkehlchen_api_server: APIServer,
        globaldb: GlobalDBHandler,
        with_custom_path: bool,
) -> None:
    """Test that the endpoint for exporting user assets works correctly"""
    eth_address = make_evm_address()
    identifier = ethaddress_to_identifier(eth_address)
    globaldb.add_asset(EvmToken.initialize(
        address=eth_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=18,
        name='yabirtoken',
        symbol='YAB',
        coingecko='YAB',
        cryptocompare='YAB',
    ))
    globaldb.add_asset(CustomAsset.initialize(
        identifier='my_custom_id',
        name='my house',
        custom_asset_type='property',
    ))
    with tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True,  # needed on windows, see https://tinyurl.com/tmp-win-err
    ) as path:
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
            result = assert_proper_sync_response_with_result(response)
            if with_custom_path:
                assert path in result['file']
            zip_file = ZipFile(result['file'])
            data = json.loads(zip_file.read('assets.json'))
            assert int(data['version']) == GLOBAL_DB_VERSION
            assert len(data['assets']) == 2
            assert {
                'identifier': identifier,
                'name': 'yabirtoken',
                'evm_chain': 'ethereum',
                'asset_type': 'evm token',
                'decimals': 18,
                'symbol': 'YAB',
                'started': None,
                'forked': None,
                'swapped_for': None,
                'cryptocompare': 'YAB',
                'coingecko': 'YAB',
                'protocol': None,
                'token_kind': 'erc20',
                'underlying_tokens': None,
                'address': eth_address,
            } in data['assets']
            assert {
                'identifier': 'my_custom_id',
                'asset_type': 'custom asset',
                'name': 'my house',
                'custom_asset_type': 'property',
                'notes': None,
            } in data['assets']
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
        result = assert_proper_sync_response_with_result(response)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('method', ['post', 'put'])
@pytest.mark.parametrize('file_type', ['zip', 'json'])
def test_importing_user_assets_list(
        rotkehlchen_api_server: APIServer,
        method: str,
        file_type: str,
) -> None:
    """Test that the endpoint for importing user assets works correctly"""
    async_query = random.choice((True, False))
    filepath = Path(__file__).resolve().parent.parent / 'data' / f'exported_assets.{file_type}'

    if method == 'put':
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'userassetsresource',
            ), json={'action': 'upload', 'file': str(filepath), 'async_query': async_query},
        )
    else:
        with open(filepath, 'rb') as infile:
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'userassetsresource',
                ), data={'async_query': async_query},
                files={'file': infile},
            )

    if async_query is True:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        assert outcome['result'] is True
    else:
        assert_simple_ok_response(response)

    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0

    assert_proper_sync_response_with_result(response)
    stinch = EvmToken('eip155:1/erc20:0xA0446D8804611944F1B527eCD37d7dcbE442caba')
    assert stinch.symbol == 'st1INCH'
    assert len(stinch.underlying_tokens) == 1
    assert stinch.decimals == 18
