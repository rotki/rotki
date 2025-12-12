from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.evm.types import EvmIndexer
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('ethereum_accounts', [[]])
def test_query_transactions_errors(rotkehlchen_api_server: 'APIServer') -> None:
    """Check various validation errors when querying blockchain transactions."""
    for json_data, error_msg in (
        (  # Untracked/malformed address with no chain specified
            {'accounts': [{'address': '0xasdasd'}]},
            'The address 0xasdasd is not tracked on any chain in rotki',
        ), (  # Untracked address with the chain specified
            {'accounts': [{'address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7', 'blockchain': 'eth'}]},  # noqa: E501
            'The address 0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7 on ethereum is not tracked in rotki',  # noqa: E501
        ), (  # Malformed address with the chain specified
            {'accounts': [{'address': '0xasdasd', 'blockchain': 'optimism'}]},
            'The address 0xasdasd is not a valid optimism address.',
        ), (  # Blockchain that we don't support transactions for yet
            {'accounts': [{'address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7', 'blockchain': 'avax'}]},  # noqa: E501
            'rotki does not support transactions for avalanche',
        ), (  # Malformed from_timestamp
            {'accounts': [{'address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7'}], 'from_timestamp': 'foo'},  # noqa: E501
            'Failed to deserialize a timestamp entry from string foo',
        ), (  # Malformed to_timestamp
            {'accounts': [{'address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7'}], 'to_timestamp': 'foo'},  # noqa: E501
            'Failed to deserialize a timestamp entry from string foo',
        ),
    ):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'blockchaintransactionsresource',
            ), json=json_data,
        )
        assert_error_response(
            response=response,
            contained_in_msg=error_msg,
            status_code=HTTPStatus.BAD_REQUEST,
        )


@pytest.mark.parametrize('have_decoders', [[True]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_decode_given_transactions_custom_indexer(rotkehlchen_api_server: 'APIServer') -> None:
    """Ensure a custom indexer is used first when redecode endpoint is called with one.
    In this test we check that the validation passes correctly the order and they are reset after
    executing the logic.
    """
    custom_indexer = EvmIndexer.ROUTESCAN
    default_order = CachedSettings().get_evm_indexers_order_for_chain(ChainID.ETHEREUM)
    assert default_order[0] != custom_indexer
    node_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer  # noqa: E501
    call_order: list[EvmIndexer] = []
    available_indexers = node_inquirer.available_indexers
    original_try_indexers = node_inquirer._try_indexers

    def tracking_try_indexers(func):
        def wrapped(indexer_api):
            for name, candidate in available_indexers.items():
                if candidate is indexer_api:
                    call_order.append(name)
                    break
            return func(indexer_api)

        return original_try_indexers(wrapped)

    with patch.object(node_inquirer, '_try_indexers', side_effect=tracking_try_indexers):
        result = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'transactionsdecodingresource',
            ), json={
                'async_query': False,
                'chain': 'eth',
                'tx_refs': ['0xc23d562c935fc3afd31a3597d647dee302421659ad9fc5ca77e2b257df400532'],
                'delete_custom': False,
                'custom_indexers_order': [custom_indexer.serialize()],
            },
        )
    outcome = assert_proper_response_with_result(
        response=result,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert outcome is True
    assert CachedSettings().get_evm_indexers_order_for_chain(ChainID.ETHEREUM) == default_order
    assert call_order == [custom_indexer]

    result = requests.put(  # test validation of indexers
        api_url_for(
            rotkehlchen_api_server,
            'transactionsdecodingresource',
        ), json={
            'async_query': False,
            'chain': 'eth',
            'tx_refs': ['0xc23d562c935fc3afd31a3597d647dee302421659ad9fc5ca77e2b257df400532'],
            'delete_custom': False,
            'custom_indexers_order': ['fakeIndexer'],
        },
    )
    assert_error_response(response=result, contained_in_msg='Invalid EVM indexer: fakeIndexer')
