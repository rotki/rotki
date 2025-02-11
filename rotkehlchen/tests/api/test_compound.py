import random
import warnings as test_warnings
from collections.abc import Sequence
from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.server import APIServer
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.decoding.compound.v3.balances import Compoundv3Balances
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_COMP
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import CURRENT_PRICE_MOCK
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import ChecksumEvmAddress, Price, deserialize_evm_tx_hash

TEST_ACC1 = '0x2bddEd18E2CA464355091266B7616956944ee7eE'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_query_compound_balances(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress] | None,
) -> None:
    """Check querying the compound balances endpoint works. Uses real data.

    TODO: Here we should use a test account for which we will know what balances
    it has and we never modify
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'compoundbalancesresource',
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=60)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_sync_response_with_result(response)

    if len(result) != 1:
        test_warnings.warn(UserWarning(f'Test account {TEST_ACC1} has no compound balances'))
        return

    lending = result[TEST_ACC1]['lending']
    for entry in lending.values():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']
    borrowing = result[TEST_ACC1]['borrowing']
    for entry in borrowing.values():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']
    rewards = result[TEST_ACC1]['rewards']
    if len(rewards) != 0:
        assert len(rewards) == 1
        assert A_COMP.identifier in rewards


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x478768685e023B8AF2815369b353b786713fDEa4',
    '0x3eab2E72fA768C3cB8ab071929AC3C8aed6CbFA6',
    '0x1107F797c1af4982b038Eb91260b3f9A90eecee9',
]])
@pytest.mark.parametrize('have_decoders', [[True]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_query_compound_v3_balances(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Check querying the compound v3 balances endpoint works. Uses real data for borrowing,
    mocked balances for lending to avoid randomness in the VCR."""
    chain_aggregator = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator
    c_usdc_v3 = EvmToken('eip155:1/erc20:0xc3d688B66703497DAA19211EEdff47f25384cdc3')
    chain_aggregator.ethereum.transactions_decoder.decode_transaction_hashes(
        ignore_cache=True,
        tx_hashes=[
            deserialize_evm_tx_hash('0x0c9276ed2a202b039d5fa6e9749fd19f631c62e8e4beccc2f4dc0358a4882bb1'),  # Borrow 3,500 USDC from cUSDCv3  # noqa: E501
            deserialize_evm_tx_hash('0x13965c2a1ba75dafa060d0bdadd332c9330b9c5819a8fee7d557a937728fa22f'),  # Borrow 42.5043 USDC from USDCv3  # noqa: E501
        ],
    )
    compound_v3_balances = Compoundv3Balances(
        evm_inquirer=chain_aggregator.ethereum.node_inquirer,
        tx_decoder=chain_aggregator.ethereum.transactions_decoder,
    )
    unique_borrows, underlying_tokens = compound_v3_balances._extract_unique_borrowed_tokens()

    def mock_extract_unique_borrowed_tokens(
            self: 'Compoundv3Balances',  # pylint: disable=unused-argument
    ) -> tuple[dict[EvmToken, list['ChecksumEvmAddress']], dict['ChecksumEvmAddress', EvmToken]]:
        return {
            token: sorted(addresses, reverse=True)  # cast set to list to avoid randomness in VCR
            for token, addresses in unique_borrows.items()
        }, underlying_tokens

    def mock_query_tokens(
            addresses: Sequence[ChecksumEvmAddress],
    ) -> tuple[dict[ChecksumEvmAddress, dict[EvmToken, FVal]], dict[EvmToken, Price]]:
        return ({
            ethereum_accounts[0]: {c_usdc_v3: FVal('333349.851793')},
            ethereum_accounts[1]: {c_usdc_v3: FVal('0.32795')},
        }, {c_usdc_v3: Price(CURRENT_PRICE_MOCK)}) if len(addresses) != 0 else ({}, {})

    with (
        patch(
            target='rotkehlchen.chain.evm.tokens.EvmTokens.query_tokens_for_addresses',
            side_effect=mock_query_tokens,
        ),
        patch(
            target='rotkehlchen.chain.evm.decoding.compound.v3.balances.Compoundv3Balances._extract_unique_borrowed_tokens',
            new=mock_extract_unique_borrowed_tokens,
        ),
    ):
        result = assert_proper_sync_response_with_result(requests.get(api_url_for(
            rotkehlchen_api_server,
            'compoundbalancesresource',
        )))

    def get_balance(amount: str) -> dict[str, str]:
        return Balance(amount=FVal(amount), usd_value=FVal(amount) * CURRENT_PRICE_MOCK).serialize()  # noqa: E501

    assert result == {
        ethereum_accounts[0]: {
            'lending': {
                c_usdc_v3.identifier: {
                    'apy': '18.62%',
                    'balance': get_balance('333349.851793'),
                },
            }, 'rewards': {
                A_COMP.identifier: {
                    'apy': None,
                    'balance': get_balance('12.317773'),
                },
            },
        }, ethereum_accounts[1]: {
            'lending': {
                c_usdc_v3.identifier: {
                    'apy': '18.62%',
                    'balance': get_balance('0.32795'),
                },
            }, 'rewards': {
                A_COMP.identifier: {
                    'apy': None,
                    'balance': get_balance('0.000016'),
                },
            },
        }, ethereum_accounts[2]: {
            'borrowing': {
                c_usdc_v3.identifier: {
                    'apy': '21.26%',
                    'balance': get_balance('22378.61881'),
                },
            }, 'lending': {}, 'rewards': {
                A_COMP.identifier: {
                    'apy': None,
                    'balance': get_balance('0.212129'),
                },
            },
        },
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_compound_balances_module_not_activated(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress] | None,
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'compoundbalancesresource',
        ))
    assert_error_response(
        response=response,
        contained_in_msg='compound module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xF59D4937BF1305856C3a267bB07791507a3377Ee']])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
@pytest.mark.parametrize('have_decoders', [[True]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_events_compound(rotkehlchen_api_server: 'APIServer') -> None:
    """
    Check that the compound endpoint correctly processes requests for stats
    """
    ethereum_transaction_decoder = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.transactions_decoder  # noqa: E501
    tx_hashes = [
        deserialize_evm_tx_hash('0x2bbb296ebf1d94ad28d54c446cb23709b3463c4a43d8b5b8438ff39b2b985e1c'),
    ]
    ethereum_transaction_decoder.decode_transaction_hashes(
        ignore_cache=True,
        tx_hashes=tx_hashes,
    )
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'modulestatsresource',
        module='compound',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert result == {
        'interest_profit': {
            '0xF59D4937BF1305856C3a267bB07791507a3377Ee': {
                'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F': {
                    'amount': '1893.678208215722372195',
                    'usd_value': '1893.678208215722372195',
                },
            },
        },
        'liquidation_profit': {},
        'debt_loss': {},
        'rewards': {
            '0xF59D4937BF1305856C3a267bB07791507a3377Ee': {
                'eip155:1/erc20:0xc00e94Cb662C3520282E6f5717214004A7f26888': {
                    'amount': '0.003613066320816938',
                    'usd_value': '0.0039537892977049775',
                },
            },
        },
    }
