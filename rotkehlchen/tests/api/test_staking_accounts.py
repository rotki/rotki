from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.solana.utils import StakeAccountInfo
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI, StakingSummary
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.types import SolanaAddress

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.types import ChecksumEvmAddress

SOLANA_OWNER = SolanaAddress('updtkJ8HAhh3rSkBCd3p9Z1Q74yJW4rMhSbScRskDPM')
VOTE_ACCOUNT = SolanaAddress('7Sys29UqSSRwczo8N4VZ3phNUtGhGdYTkKMGCR4bx6wH')
HYPERLIQUID_STAKER = string_to_evm_address('0x000000000056f99d36B6F2e0c51FD41496BbacB8')


@pytest.mark.parametrize('solana_accounts', [[SOLANA_OWNER]])
def test_solana_stake_accounts(rotkehlchen_api_server: APIServer) -> None:
    """Amounts are SOL strings, an undelegated account has no validator and results are
    keyed by the owner of the stake accounts."""
    def make_stake_account(address: str, lamports: int, voter: SolanaAddress | None) -> StakeAccountInfo:  # noqa: E501
        return StakeAccountInfo(
            address=SolanaAddress(address),
            lamports=lamports,
            staker=SOLANA_OWNER,
            withdrawer=SOLANA_OWNER,
            voter=voter,
        )

    with patch.object(
        rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.solana,
        'get_stake_accounts_by_owner',
        return_value={SOLANA_OWNER: [
            make_stake_account('StakeAcc1111111111111111111111111111111111111', 8_500_000_000, VOTE_ACCOUNT),  # noqa: E501
            make_stake_account('StakeAcc2222222222222222222222222222222222222', 1_000_000_000, None),  # noqa: E501
        ]},
    ):
        result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'solanastakeaccountsresource'),
        ))

    assert result == {SOLANA_OWNER: [{
        'address': 'StakeAcc1111111111111111111111111111111111111',
        'amount': '8.5',
        'validator': VOTE_ACCOUNT,
    }, {
        'address': 'StakeAcc2222222222222222222222222222222222222',
        'amount': '1',
        'validator': None,
    }]}


@pytest.mark.parametrize('solana_accounts', [[SOLANA_OWNER]])
def test_solana_stake_accounts_remote_error(rotkehlchen_api_server: APIServer) -> None:
    with patch.object(
        rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.solana,
        'get_stake_accounts_by_owner',
        side_effect=RemoteError('rpc down'),
    ):
        response = requests.get(api_url_for(rotkehlchen_api_server, 'solanastakeaccountsresource'))

    assert_error_response(response=response, contained_in_msg='rpc down', status_code=HTTPStatus.BAD_GATEWAY)  # noqa: E501


@pytest.mark.parametrize('hyperliquid_accounts', [[HYPERLIQUID_STAKER]])
def test_hyperliquid_staking_summaries(
        rotkehlchen_api_server: APIServer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
) -> None:
    """The three states are returned apart, keyed by address, with snake case keys."""
    with patch.object(
        HyperliquidAPI,
        'query_staking_summary',
        return_value=StakingSummary(
            delegated=FVal('10.5'),
            undelegated=FVal('2.25'),
            pending_withdrawal=FVal(1),
        ),
    ):
        result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'hyperliquidstakingsummariesresource'),
        ))

    assert result == {hyperliquid_accounts[0]: {
        'delegated': '10.5',
        'undelegated': '2.25',
        'pending_withdrawal': '1',
    }}


@pytest.mark.parametrize('hyperliquid_accounts', [[HYPERLIQUID_STAKER]])
def test_hyperliquid_staking_summaries_remote_error(rotkehlchen_api_server: APIServer) -> None:
    with patch.object(
        HyperliquidAPI,
        'query_staking_summary',
        side_effect=RemoteError('api down'),
    ):
        response = requests.get(
            api_url_for(rotkehlchen_api_server, 'hyperliquidstakingsummariesresource'),
        )

    assert_error_response(response=response, contained_in_msg='api down', status_code=HTTPStatus.BAD_GATEWAY)  # noqa: E501
