from http import HTTPStatus
from typing import TYPE_CHECKING, Final
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.ethereum import INFURA_ETH_NODE
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


TEST_ADDRESS: Final = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'  # vitalik.eth
HISTORICAL_TS: Final = Timestamp(1609459200)  # January 1, 2021


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDRESS]])
def test_get_onchain_historical_balance(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[str],
) -> None:
    address = ethereum_accounts[0]
    node_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer  # noqa: E501
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db

    def _assert_historical_balance_cache_entry(
            asset_id: str,
            expected_amount: str,
    ) -> None:
        with db.conn.read_ctx() as cursor:
            row = cursor.execute(
                'SELECT amount, timestamp FROM historical_balance_cache '
                'WHERE blockchain=? AND address=? AND asset=? AND timestamp=?',
                (node_inquirer.blockchain.value, address, asset_id, HISTORICAL_TS),
            ).fetchone()
        assert row is not None
        assert row[0] == expected_amount
        assert row[1] == HISTORICAL_TS

    dai_token = A_DAI.resolve_to_evm_token()
    for payload, error_msg in (
        ({'timestamp': ts_now() + DAY_IN_SECONDS, 'evm_chain': 'ethereum', 'address': address, 'asset': A_ETH.identifier}, 'Timestamp cannot be in the future'),  # noqa: E501
        ({'timestamp': HISTORICAL_TS, 'evm_chain': 'ethereum', 'address': address, 'asset': 'eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'}, 'is not on the ethereum'),  # noqa: E501
        ({'timestamp': HISTORICAL_TS, 'evm_chain': 'btc', 'address': address, 'asset': 'BTC'}, 'Failed to deserialize evm chain value btc'),  # noqa: E501
        ({'timestamp': dai_token.started - 1, 'evm_chain': 'ethereum', 'address': address, 'asset': A_DAI.identifier}, 'did not exist at timestamp'),  # type: ignore[operator]  # `started` cannot be None  # noqa: E501
    ):
        assert_error_response(
            response=requests.post(
                api_url_for(rotkehlchen_api_server, 'onchainhistoricalbalanceresource'),
                json=payload,
            ),
            contained_in_msg=error_msg,
            status_code=HTTPStatus.BAD_REQUEST,
        )

    with patch.object(node_inquirer, 'has_archive_node', return_value=False):
        assert_error_response(
            response=requests.post(
                api_url_for(rotkehlchen_api_server, 'onchainhistoricalbalanceresource'),
                json={'timestamp': HISTORICAL_TS, 'evm_chain': 'ethereum', 'address': address, 'asset': A_ETH.identifier},  # noqa: E501
            ),
            contained_in_msg='No archive node available',
            status_code=HTTPStatus.CONFLICT,
        )

    result = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'onchainhistoricalbalanceresource'),
        json={'timestamp': HISTORICAL_TS, 'evm_chain': 'ethereum', 'address': address, 'asset': A_ETH.identifier},  # noqa: E501
    ))
    assert result[A_ETH] == '8.275127966894157145'
    _assert_historical_balance_cache_entry(
        asset_id=A_ETH.identifier,
        expected_amount=result[A_ETH],
    )

    result = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'onchainhistoricalbalanceresource'),
        json={'timestamp': HISTORICAL_TS, 'evm_chain': 'ethereum', 'address': address, 'asset': A_DAI.identifier},  # noqa: E501
    ))
    assert result[A_DAI] == '6.169011805555555325'
    _assert_historical_balance_cache_entry(
        asset_id=A_DAI.identifier,
        expected_amount=result[A_DAI],
    )


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDRESS]])
def test_onchain_historical_balance_failure_keeps_its_cause(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """A rate limited archive node says so, rather than every failure reading as network,
    and a balanceOf call that reverts reads as the node refusing it."""
    node_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer  # noqa: E501
    with (
        patch.object(node_inquirer, 'has_archive_node', return_value=True),
        patch.object(node_inquirer, 'get_blocknumber_by_time', return_value=11565019),
        patch.object(node_inquirer, 'query_historical_native_balance', side_effect=RemoteError(
            'slow down',
            cause=FailureCause.RATE_LIMITED,
        )),
    ):
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'onchainhistoricalbalanceresource'),
            json={'timestamp': HISTORICAL_TS, 'evm_chain': 'ethereum', 'address': ethereum_accounts[0], 'asset': A_ETH.identifier},  # noqa: E501
        )
    assert_error_response(response=response, contained_in_msg='slow down', status_code=HTTPStatus.CONFLICT)  # noqa: E501
    assert response.json()['cause'] == FailureCause.RATE_LIMITED

    with (
        patch.object(node_inquirer, 'get_archive_call_order', return_value=[object()]),
        patch.object(node_inquirer, 'call_contract', side_effect=BlockchainQueryError('reverted')),
        pytest.raises(RemoteError) as raised,
    ):
        node_inquirer.query_historical_token_balance(
            address=ethereum_accounts[0],
            token=A_DAI.resolve_to_evm_token(),
            block_number=1,
        )
    assert raised.value.cause == FailureCause.REMOTE_REJECTED
