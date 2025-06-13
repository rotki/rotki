from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.evm.types import string_to_evm_address
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

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def _get_timestamps(db: DBEns, addresses: list[ChecksumEvmAddress]) -> list[Timestamp]:
    timestamps = []
    with db.db.conn.read_ctx() as cursor:
        for value in db.get_reverse_ens(
            cursor=cursor,
            addresses=addresses,
        ).values():
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
        return dbens.update_values(
            write_cursor=write_cursor,
            ens_lookup_results=query_results,
            mappings_to_send=ens_mappings,
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2024-04-11 23:00:00 GMT')
def test_reverse_ens(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that we can reverse resolve ENS names"""
    db = DBEns(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    addrs_1 = [
        string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306'),
        string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
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
            string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306'),
            string_to_evm_address('0xA4b73b39F73F73655e9fdC5D167c21b3fA4A1eD6'),
            string_to_evm_address('0x71C7656EC7ab88b098defB751B7401B5f6d8976F'),
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

        with patch(
            target='rotkehlchen.db.ens.DBEns.add_ens_mapping',
            side_effect=db.add_ens_mapping,
        ) as patched_add_ens_mapping:
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'reverseensresource',
                ),
                json={'ethereum_addresses': addrs_1 + addrs_2[1:], 'ignore_cache': True},
            )
            assert_proper_sync_response_with_result(response)
            # Check that we update mappings for all 4 addresses
            assert patched_add_ens_mapping.call_count == 4


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2025-03-31 12:00:00 GMT')
def test_resolve_ens(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that we can resolve ENS names"""
    dbens = DBEns(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'resolveensresource',
        ),
        json={'name': 'lefteris.eth'},
    )
    with dbens.db.conn.read_ctx() as cursor:  # make sure it's also in the DB
        assert dbens.get_address_for_name(cursor, 'lefteris.eth') == '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'  # noqa: E501

    result = assert_proper_sync_response_with_result(response)
    assert result == '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'resolveensresource',
        ),
        json={'name': 'isurelydontexistbecauseifid1drotkitestswouldbreak.eth'},
    )
    result = assert_error_response(response, status_code=HTTPStatus.NOT_FOUND, result_exists=False)
    assert result is None
    with dbens.db.conn.read_ctx() as cursor:  # make sure it's also NOT in the DB
        assert dbens.get_address_for_name(cursor, 'isurelydontexistbecauseifid1drotkitestswouldbreak.eth') is None  # noqa: E501
