from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import requests

from rotkehlchen.constants.misc import AVATARIMAGESDIR_NAME, IMAGESDIR_NAME
from rotkehlchen.db.ens import DBEns
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ProtocolsWithCache
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_icons_and_avatars_cache_deletion(rotkehlchen_api_server: 'APIServer') -> None:
    """Checks that clearing the cache for avatars and icons work as expected."""
    icons_dir = rotkehlchen_api_server.rest_api.rotkehlchen.icon_manager.icons_dir
    data_dir = rotkehlchen_api_server.rest_api.rotkehlchen.data_dir
    avatars_dir = data_dir / IMAGESDIR_NAME / AVATARIMAGESDIR_NAME
    avatars_dir.mkdir(exist_ok=True)

    dbens = DBEns(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with dbens.db.user_write() as write_cursor:
        dbens.add_ens_mapping(
            write_cursor=write_cursor,
            address=make_evm_address(),
            name='nebolax.eth',
            now=ts_now(),
        )

        write_cursor.execute(
            'UPDATE ens_mappings SET last_avatar_update=? WHERE ens_name=?',
            (ts_now(), 'nebolax.eth'),
        )

    # populate icons dir
    Path(f'{icons_dir}/ETH_small.png').write_bytes(b'')
    Path(f'{icons_dir}/BTC_small.png').write_bytes(b'')
    Path(f'{icons_dir}/AVAX_small.png').write_bytes(b'')
    # also add an avatar, to make sure it's not deleted when icons are
    Path(f'{avatars_dir}/me.eth.png').write_bytes(b'')

    assert len([i for i in icons_dir.iterdir() if i.is_file()]) == 3
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'clearcacheresource',
            cache_type='icons',
        ), json={
            'entries': ['ETH'],
        },
    )
    assert_proper_response(response)
    assert len([i for i in icons_dir.iterdir() if i.is_file()]) == 2
    assert len([i for i in avatars_dir.iterdir() if i.is_file()]) == 1

    # delete icons cache completely
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'clearcacheresource',
            cache_type='icons',
        ),
    )
    assert_proper_response(response)
    assert len([i for i in icons_dir.iterdir() if i.is_file()]) == 0
    assert len([i for i in avatars_dir.iterdir() if i.is_file()]) == 1

    # populate avatars dir to test the cache deletion
    Path(f'{avatars_dir}/ava.eth.png').write_bytes(b'')
    Path(f'{avatars_dir}/prettyirrelevant.eth.png').write_bytes(b'')
    Path(f'{avatars_dir}/nebolax.eth.png').write_bytes(b'')

    assert len([i for i in avatars_dir.iterdir() if i.is_file()]) == 4
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'clearcacheresource',
            cache_type='avatars',
        ), json={
            'entries': ['ava.eth'],
        },
    )
    assert_proper_response(response)
    assert len([i for i in avatars_dir.iterdir() if i.is_file()]) == 3

    # delete avatars cache completely
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'clearcacheresource',
            cache_type='avatars',
        ),
    )
    assert_proper_response(response)
    assert len([i for i in avatars_dir.iterdir() if i.is_file()]) == 0

    # now try fetching the avatar and see it works
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ensavatarsresource',
            ens_name='nebolax.eth',
        ),
    )
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'image/png'


def test_protocol_data_refresh(rotkehlchen_api_server: 'APIServer') -> None:
    """Tests that refreshing the protocol data works as expected"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'protocoldatarefreshresource',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert {
        'curve',
        'velodrome',
        'convex',
        'aerodrome',
        'gearbox',
        'yearn',
        'maker',
        'eth withdrawals',
        'eth blocks',
        'spark',
        'balancer v1',
        'balancer v2',
        'balancer v3',
    }.issubset(set(result))

    with ExitStack() as stack:
        stack.enter_context(patch(
            'rotkehlchen.chain.evm.node_inquirer.should_update_protocol_cache',
            new=MagicMock(return_value=False),
        ))
        patched_convex_query = stack.enter_context(patch(
            'rotkehlchen.api.rest.query_convex_data',
            new=MagicMock(),
        ))
        patched_curve_query = stack.enter_context(patch(
            'rotkehlchen.api.rest.query_curve_data',
            new=MagicMock(),
        ))
        patched_velodrome_query = stack.enter_context(patch(
            'rotkehlchen.api.rest.query_velodrome_like_data',
            new=MagicMock(),
        ))
        patched_gearbox_query = stack.enter_context(patch(
            'rotkehlchen.api.rest.query_gearbox_data',
            new=MagicMock(),
        ))
        patched_query_yearn_vaults = stack.enter_context(patch(
            'rotkehlchen.api.rest.query_yearn_vaults',
            new=MagicMock(),
        ))
        patched_ilk_registry = stack.enter_context(patch(
            'rotkehlchen.api.rest.query_ilk_registry_and_maybe_update_cache',
            new=MagicMock(),
        ))
        patched_aave_v3_assets = stack.enter_context(patch(
            'rotkehlchen.api.rest.update_aave_v3_underlying_assets',
            new=MagicMock(),
        ))
        patched_spark_assets = stack.enter_context(patch(
            'rotkehlchen.api.rest.update_spark_underlying_assets',
            new=MagicMock(),
        ))
        patched_eth_withdrawals_cache = stack.enter_context(patch.object(
            rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
            'delete_dynamic_caches',
            new=MagicMock(),
        ))
        patched_balancer_query = stack.enter_context(patch(
            'rotkehlchen.api.rest.query_balancer_data',
            new=MagicMock(),
        ))
        patched_merkl_cache = stack.enter_context(patch(
            'rotkehlchen.api.rest.GlobalDBHandler',
            new=MagicMock(),
        ))

        for protocol, patched_obj, expected_calls in (
            (ProtocolsWithCache.CURVE, patched_curve_query, 6),
            (ProtocolsWithCache.CONVEX, patched_convex_query, 1),
            (ProtocolsWithCache.GEARBOX, patched_gearbox_query, 1),
            (ProtocolsWithCache.VELODROME, patched_velodrome_query, 1),
            (ProtocolsWithCache.AERODROME, patched_velodrome_query, 1),
            (ProtocolsWithCache.YEARN, patched_query_yearn_vaults, 1),
            (ProtocolsWithCache.MAKER, patched_ilk_registry, 1),
            (ProtocolsWithCache.AAVE, patched_aave_v3_assets, 1),
            (ProtocolsWithCache.SPARK, patched_spark_assets, 1),
            (ProtocolsWithCache.ETH_WITHDRAWALS, patched_eth_withdrawals_cache, 1),
            (ProtocolsWithCache.ETH_BLOCKS, patched_eth_withdrawals_cache, 1),
            (ProtocolsWithCache.BALANCER_V1, patched_balancer_query, 3),  # supported on 3 chains
            (ProtocolsWithCache.BALANCER_V2, patched_balancer_query, 6),  # supported on 6 chains
            (ProtocolsWithCache.BALANCER_V3, patched_balancer_query, 5),  # supported on 5 chains
            (ProtocolsWithCache.MERKL, patched_merkl_cache, 1),
        ):
            patched_obj.reset_mock()
            response = requests.post(api_url_for(
                rotkehlchen_api_server,
                'protocoldatarefreshresource',
            ), json={'cache_protocol': protocol.serialize()})
            assert_proper_response(response)
            assert patched_obj.call_count == expected_calls, f'{protocol} should have been queried {expected_calls} but had {patched_obj.call_count} calls'  # noqa: E501
