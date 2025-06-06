from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_error_response

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
