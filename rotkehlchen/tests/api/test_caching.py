from contextlib import ExitStack
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import requests

from rotkehlchen.db.ens import DBEns
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_icons_and_avatars_cache_deletion(rotkehlchen_api_server):
    """Checks that clearing the cache for avatars and icons work as expected."""
    icons_dir = rotkehlchen_api_server.rest_api.rotkehlchen.icon_manager.icons_dir
    avatars_dir = icons_dir / 'avatars'
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
    with open(f'{icons_dir}/ETH_small.png', 'wb') as f:
        f.write(b'')

    with open(f'{icons_dir}/BTC_small.png', 'wb') as f:
        f.write(b'')

    with open(f'{icons_dir}/AVAX_small.png', 'wb') as f:
        f.write(b'')

    # also add an avatar, to make sure it's not deleted when icons are
    with open(f'{avatars_dir}/me.eth.png', 'wb') as f:
        f.write(b'')

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
    with open(f'{avatars_dir}/ava.eth.png', 'wb') as f:
        f.write(b'')

    with open(f'{avatars_dir}/prettyirrelevant.eth.png', 'wb') as f:
        f.write(b'')

    with open(f'{avatars_dir}/nebolax.eth.png', 'wb') as f:
        f.write(b'')

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


@pytest.mark.vcr()
def test_general_cache_refresh(rotkehlchen_api_server: 'APIServer'):
    """Tests that refreshing the general cache works as expected"""
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
            'rotkehlchen.api.rest.query_velodrome_data',
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

        response = requests.post(api_url_for(
            rotkehlchen_api_server,
            'refreshgeneralcacheresource',
        ))
        assert_proper_response(response)
        assert patched_convex_query.call_count == 1, 'Convex pools should have been queried despite should_update_protocol_cache being False'  # noqa: E501
        assert patched_curve_query.call_count == 1, 'Curve pools should have been queried despite should_update_protocol_cache being False'  # noqa: E501
        assert patched_velodrome_query.call_count == 1, 'Velodrome pools should have been queried despite should_update_protocol_cache being False'  # noqa: E501
        assert patched_query_yearn_vaults.call_count == 1, 'Yearn vaults refresh should have been triggered'  # noqa: E501
        assert patched_ilk_registry.call_count == 1, 'Ilk registry refresh should have been triggered'  # noqa: E501
