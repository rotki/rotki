from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.constants.timing import ENS_UPDATE_INTERVAL
from rotkehlchen.db.ens import DBEns
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.types import ChecksumEvmAddress, EnsMapping, Timestamp
from rotkehlchen.utils.misc import ts_now


def _get_timestamps(db: DBEns, addresses: list[ChecksumEvmAddress]):
    timestamps = []
    with db.db.conn.read_ctx() as cursor:
        for value in db.get_reverse_ens(cursor, addresses).values():
            if isinstance(value, int):
                timestamps.append(value)
            else:
                timestamps.append(value.last_update)

    return timestamps


def mocked_find_ens_mappings(
        ethereum_inquirer: EthereumInquirer,
        addresses: list[ChecksumEvmAddress],
        ignore_cache: bool,
) -> dict[ChecksumEvmAddress, str]:
    """If find_ens_mappings changes then so should this implementation

    The only thing this does is to add a sort for addresses to query so it can be vcred.
    We don't add this sort in actual production code since it's not needed and we
    should not change production code to cater for tests.
    """
    dbens = DBEns(ethereum_inquirer.database)
    ens_mappings: dict[ChecksumEvmAddress, str] = {}
    if ignore_cache:
        addresses_to_query = addresses
    else:
        addresses_to_query = []
        with dbens.db.conn.read_ctx() as cursor:
            cached_data = dbens.get_reverse_ens(cursor=cursor, addresses=addresses)
        cur_time = ts_now()
        for address, cached_value in cached_data.items():
            has_name = isinstance(cached_value, EnsMapping)
            last_update: Timestamp = cached_value.last_update if has_name else cached_value  # type: ignore  # mypy doesn't see `isinstance` check
            if cur_time - last_update > ENS_UPDATE_INTERVAL:
                addresses_to_query.append(address)
            elif has_name:
                ens_mappings[cached_value.address] = cached_value.name  # type: ignore
        addresses_to_query += list(set(addresses) - set(cached_data.keys()))
        addresses_to_query.sort()

    try:
        query_results = ethereum_inquirer.ens_reverse_lookup(addresses_to_query)
    except (RemoteError, BlockchainQueryError) as e:
        raise RemoteError(f'Error occurred while querying ens names: {e!s}') from e

    with dbens.db.user_write() as write_cursor:
        ens_mappings = dbens.update_values(
            write_cursor=write_cursor,
            ens_lookup_results=query_results,
            mappings_to_send=ens_mappings,
        )
    return ens_mappings


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2024-04-11 23:00:00 GMT')
def test_reverse_ens(rotkehlchen_api_server):
    """Test that we can reverse resolve ENS names"""
    db = DBEns(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    db_conn = rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn
    addrs_1 = [
        '0x9531C059098e3d194fF87FebB587aB07B30B1306',
        '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    ]
    with patch('rotkehlchen.api.rest.find_ens_mappings', wraps=mocked_find_ens_mappings):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'reverseensresource',
            ),
            json={'ethereum_addresses': addrs_1},
        )
        result = assert_proper_sync_response_with_result(response)
        expected_resp_1 = {
            addrs_1[0]: 'rotki.eth',
            addrs_1[1]: 'lefteris.eth',
        }
        assert result == expected_resp_1

        addrs_2 = [
            '0x9531C059098e3d194fF87FebB587aB07B30B1306',
            '0xA4b73b39F73F73655e9fdC5D167c21b3fA4A1eD6',
            '0x71C7656EC7ab88b098defB751B7401B5f6d8976F',
        ]
        timestamps_before_request = _get_timestamps(db, addrs_1)
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'reverseensresource',
            ),
            json={'ethereum_addresses': addrs_2},
        )
        result = assert_proper_sync_response_with_result(response)
        expected_resp_2 = {
            addrs_2[0]: 'rotki.eth',
            addrs_2[1]: 'abc.eth',
        }
        assert result == expected_resp_2
        timestamps_after_request = _get_timestamps(db, addrs_1)
        assert timestamps_before_request == timestamps_after_request

        # Going to check that after request with ignore_cache ens_mappings will be updated
        db_changes_before = db_conn.total_changes

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'reverseensresource',
            ),
            json={'ethereum_addresses': ['0xqwerty']},
        )
        assert_error_response(
            response=response,
            contained_in_msg='Given value 0xqwerty is not an ethereum address',
            status_code=HTTPStatus.BAD_REQUEST,
        )

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'reverseensresource',
            ),
            json={'ethereum_addresses': addrs_1 + addrs_2[1:], 'ignore_cache': True},
        )
        assert_proper_sync_response_with_result(response)
    db_changes_after = db_conn.total_changes
    # Check that we have 5 updates because we have 5 rows in ens_mappings table
    assert db_changes_after == 5 + db_changes_before
