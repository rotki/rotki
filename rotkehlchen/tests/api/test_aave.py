import random
from contextlib import ExitStack
from http import HTTPStatus
from typing import TYPE_CHECKING, Final
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.server import APIServer
from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.defi.structures import (
    DefiBalance,
    DefiProtocol,
    DefiProtocolBalances,
)
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.tokens import TokenBalancesType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_DAI, A_USDC, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    Price,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

AAVE_BALANCESV1_TEST_ACC: Final = '0xC2cB1040220768554cf699b0d863A3cd4324ce32'
AAVE_BALANCESV2_TEST_ACC: Final = '0xf2d02719309c8d5F22498c2d432eDc8eB8683d83'
AAVE_BALANCESV3_TEST_ACC: Final = '0x18FD4323ea221cD05Fb275256C8f3A0740D0Aaa2'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    AAVE_BALANCESV1_TEST_ACC, AAVE_BALANCESV2_TEST_ACC, AAVE_BALANCESV3_TEST_ACC,
]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
def test_query_aave_balances(rotkehlchen_api_server: APIServer) -> None:
    """Check querying the aave balances endpoint works. Uses real data for v1/v2,
    and mocked for v3 because that need underlying tokens mapping and token balances in db."""
    a_eth_weth = get_or_create_evm_token(
        userdb=rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
        evm_address=string_to_evm_address('0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        symbol='aEthWETH',
        protocol=CPT_AAVE_V3,
        underlying_tokens=[UnderlyingToken(
            address=A_WETH.resolve_to_evm_token().evm_address,
            token_kind=EvmTokenKind.ERC20,
            weight=ONE,
        )],
    )
    variable_debt_eth_usdc = get_or_create_evm_token(
        userdb=rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
        evm_address=string_to_evm_address('0x72E95b8931767C79bA4EeE721354d6E99a61D004'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        symbol='variableDebtEthUSDC',
        protocol=CPT_AAVE_V3,
        underlying_tokens=[UnderlyingToken(
            address=A_USDC.resolve_to_evm_token().evm_address,
            token_kind=EvmTokenKind.ERC20,
            weight=ONE,
        )],
    )
    aave_prices = {a_eth_weth: Price(FVal(0.1)), variable_debt_eth_usdc: Price(FVal(10))}

    def mock_token_balances(addresses: 'Sequence[ChecksumEvmAddress]') -> TokenBalancesType:
        return {
            addresses[2]: {a_eth_weth: FVal(123), variable_debt_eth_usdc: FVal(456)},
        }, aave_prices

    with patch.object(
        target=rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.get_evm_manager(chain_id=ChainID.ETHEREUM).tokens,
        attribute='query_tokens_for_addresses',
        new=mock_token_balances,
    ):
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'aavebalancesresource',
        ))

    assert assert_proper_sync_response_with_result(response) == {
        AAVE_BALANCESV1_TEST_ACC: {
            'lending': {
                A_DAI.identifier: {
                    'balance': Balance(
                        amount=FVal('21528.498187325929022298'),
                        usd_value=FVal('32292.7472809888935334470'),
                    ).serialize(),
                    'apy': '0.00%',
                },
            },
            'borrowing': {},
        },
        AAVE_BALANCESV3_TEST_ACC: {
            'lending': {
                A_WETH.identifier: {
                    'balance': Balance(
                        amount=FVal('123'),
                        usd_value=FVal('12.3'),
                    ).serialize(),
                    'apy': '1.83%',
                },
            },
            'borrowing': {
                A_USDC.identifier: {
                    'balance': Balance(
                        amount=FVal('456'),
                        usd_value=FVal('4560'),
                    ).serialize(),
                    'stable_apr': '0.00%',
                    'variable_apr': '13.67%',
                },
            },
        },
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[AAVE_BALANCESV1_TEST_ACC]])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_aave_balances_module_not_activated(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress] | None,
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
        ethereum_accounts: list[ChecksumEvmAddress] | None,
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
                    token_address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
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
                    token_address=string_to_evm_address('0x9ff58f4fFB29fA2266Ab25e75e2A8b3503311656'),
                    token_name='Aave interest bearing WBTC',
                    token_symbol='aWBTC',
                    balance=Balance(
                        amount=FVal(0.59425326),
                        usd_value=FVal(0.891379890),
                    ),
                ),
                underlying_balances=[
                    DefiBalance(
                        token_address=string_to_evm_address('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
    assert result == {
        '0xe903fEed7c1098Ba92E4b7092ca77bBc48503d90': {
            'total_earned_interest': {
                'eip155:1/erc20:0x030bA81f1c18d280636F32af80b9AAd02Cf0854e': {
                    'amount': '0.000000179425508819',
                    'usd_value': '0.0000002691382632285',
                },
            },
            'total_lost': {
                'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F': {
                    'amount': '0.085753899141957679',
                    'usd_value': '0.1286308487129365185',
                },
                'ETH': {
                    'amount': '0.2',
                    'usd_value': '0.30',
                },
            },
            'total_earned_liquidations': {},
        },
    }
