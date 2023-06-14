import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus
from typing import Any, Optional

import pytest
import requests
from flaky import flaky

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.ethereum.defi.structures import (
    DefiBalance,
    DefiProtocol,
    DefiProtocolBalances,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import ChecksumEvmAddress, deserialize_evm_tx_hash

AAVE_BALANCESV1_TEST_ACC = '0xC2cB1040220768554cf699b0d863A3cd4324ce32'
AAVE_BALANCESV2_TEST_ACC = '0x8Fe178db26ebA2eEdb22575265bf10A63c395a3d'
AAVE_V2_TEST_ACC = '0x008C00c45D461d7E08acBC4755a4A0a3a94115ee'


@flaky(max_runs=3, min_passes=1)  # open nodes some times time out
@pytest.mark.parametrize('ethereum_accounts', [[AAVE_BALANCESV1_TEST_ACC, AAVE_BALANCESV2_TEST_ACC]])  # noqa: E501
@pytest.mark.parametrize('ethereum_modules', [['aave']])
def test_query_aave_balances(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: Optional[list[ChecksumEvmAddress]],
) -> None:
    """Check querying the aave balances endpoint works. Uses real data.

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
            'aavebalancesresource',
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    if len(result) == 0:
        test_warnings.warn(UserWarning(f'Test account {AAVE_BALANCESV1_TEST_ACC} and {AAVE_BALANCESV2_TEST_ACC} have no aave balances'))  # noqa: E501
        return

    def _assert_valid_entries(balances: dict[str, Any]) -> None:
        lending = v1_balances['lending']
        for _, entry in lending.items():
            assert len(entry) == 2
            assert len(entry['balance']) == 2
            assert 'amount' in entry['balance']
            assert 'usd_value' in entry['balance']
            assert '%' in entry['apy']
        borrowing = balances['borrowing']
        for _, entry in borrowing.items():
            assert len(entry) == 3
            assert len(entry['balance']) == 2
            assert 'amount' in entry['balance']
            assert 'usd_value' in entry['balance']
            assert '%' in entry['variable_apr']
            assert '%' in entry['stable_apr']

    v1_balances = result.get(AAVE_BALANCESV1_TEST_ACC)
    if v1_balances:
        _assert_valid_entries(v1_balances)
    else:
        test_warnings.warn(UserWarning(f'Test account {AAVE_BALANCESV1_TEST_ACC} has no aave v1 balances'))  # noqa: E501

    v2_balances = result.get(AAVE_BALANCESV2_TEST_ACC)
    if v2_balances:
        _assert_valid_entries(v2_balances)
    else:
        test_warnings.warn(UserWarning(f'Test account {AAVE_BALANCESV2_TEST_ACC} has no aave v2 balances'))  # noqa: E501


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_BALANCESV1_TEST_ACC]])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_aave_balances_module_not_activated(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: Optional[list[ChecksumEvmAddress]],
) -> None:
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'aavebalancesresource',
        ), json={'async_query': async_query})

        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['result'] is None
            assert outcome['message'] == 'aave module is not activated'
        else:
            assert_error_response(
                response=response,
                contained_in_msg='aave module is not activated',
                status_code=HTTPStatus.CONFLICT,
            )


@pytest.mark.parametrize('ethereum_accounts', [['0x01471dB828Cfb96Dcf215c57a7a6493702031EC1']])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
def test_query_aave_defi_borrowing(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: Optional[list[ChecksumEvmAddress]],
) -> None:
    """Checks that the apr/apy values are correctly returned from the API for a mocked position"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    addrs = string_to_evm_address('0x01471dB828Cfb96Dcf215c57a7a6493702031EC1')
    defi_balances = {
        addrs: [
            DefiProtocolBalances(
                protocol=DefiProtocol(
                    name='Aave V2 • Variable Debt',
                    description='Decentralized lending & borrowing protocol',
                    url='aave.com',
                    version=4,
                ),
                balance_type='Debt',
                base_balance=DefiBalance(
                    token_address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),  # noqa: E501
                    token_name='Tether USD',
                    token_symbol='USDT',
                    balance=Balance(
                        amount=FVal(2697.800279),
                        usd_value=FVal(4046.7004185),
                    ),
                ),
                underlying_balances=[],
            ),
            DefiProtocolBalances(
                protocol=DefiProtocol(
                    name='Aave V2',
                    description='Decentralized lending & borrowing protocol',
                    url='aave.com',
                    version=3,
                ),
                balance_type='Asset',
                base_balance=DefiBalance(
                    token_address=string_to_evm_address('0x9ff58f4fFB29fA2266Ab25e75e2A8b3503311656'),  # noqa: E501
                    token_name='Aave interest bearing WBTC',
                    token_symbol='aWBTC',
                    balance=Balance(
                        amount=FVal(0.59425326),
                        usd_value=FVal(0.891379890),
                    ),
                ),
                underlying_balances=[
                    DefiBalance(
                        token_address=string_to_evm_address('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),  # noqa: E501
                        token_name='Wrapped BTC',
                        token_symbol='WBTC',
                        balance=Balance(
                            amount=FVal(0.59425326),
                            usd_value=FVal(0.891379890),
                        ),
                    ),
                ],
            ),
        ],
    }

    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        defi_balances=defi_balances,
    )

    response = None
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'aavebalancesresource',
        ))

    assert response is not None
    result = assert_proper_response_with_result(response)
    account_data = result[addrs]
    assert len(account_data['lending']) == 1
    assert len(account_data['borrowing']) == 1
    variable_borrowing = account_data['borrowing']['eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7']  # noqa: E501
    assert variable_borrowing['variable_apr'] == '3.75%'
    assert variable_borrowing['stable_apr'] == '11.87%'
    assert variable_borrowing['balance']['amount'] == '2697.800279'
    variable_borrowing = account_data['lending']['eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599']  # noqa: E501
    assert variable_borrowing['apy'] == '0.12%'
    assert variable_borrowing['balance']['amount'] == '0.59425326'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xe903fEed7c1098Ba92E4b7092ca77bBc48503d90']])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('have_decoders', [[True]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_events_aave_v2(rotkehlchen_api_server: 'APIServer') -> None:
    """
    Check that the endpoint for aave stats work properly and that the results are
    correct for a subset of aave v2 events
    """
    ethereum_transaction_decoder = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.transactions_decoder  # noqa: E501
    tx_hashes = [
        deserialize_evm_tx_hash('0xefc9040c100829a391a636f02eb96a9361bd0bc2ca5e8e5f97bbc4a1831cdec9'),
        deserialize_evm_tx_hash('0xd2b0d22e915f51ce2bc24ed98c2b9139738801cff954e2e1d119e391f0dd3033'),
        deserialize_evm_tx_hash('0x819ca151c78219bbb4afdc337cc160efd55205dfe5ca151caf4661a517a41807'),
        deserialize_evm_tx_hash('0x560cfb03e9488497c8d0295b332452c42f153dafbcb3abf32441d154ddb39087'),
    ]
    ethereum_transaction_decoder.decode_transaction_hashes(
        ignore_cache=True,
        tx_hashes=tx_hashes,
    )
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'modulestatsresource',
        module='aave',
    ))
    result = assert_proper_response_with_result(response)
    assert result == {
        '0xe903fEed7c1098Ba92E4b7092ca77bBc48503d90': {
            'total_earned_interest': {
                'eip155:1/erc20:0x030bA81f1c18d280636F32af80b9AAd02Cf0854e': {
                    'amount': '0.000000127608703858',
                    'usd_value': '0.0000001914130557870',
                },
            },
            'total_lost': {
                'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F': {
                    'amount': '0.085033793839969583',
                    'usd_value': '0.1275506907599543745',
                },
            },
            'total_earned_liquidations': {},
        },
    }
