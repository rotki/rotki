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
from rotkehlchen.chain.ethereum.modules.aave.aave import Aave
from rotkehlchen.chain.ethereum.modules.aave.common import AaveBalances
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
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import ChecksumEvmAddress, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

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


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('have_decoders', [[True]])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_events(rotkehlchen_api_server: 'APIServer'):
    node_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer  # noqa: E501
    ethereum_transaction_decoder = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.transactions_decoder  # noqa: E501
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    tx_hashes = [
        deserialize_evm_tx_hash('0x8b72307967c4f7a486c1cb1b6ebca5e549de06e02930ece0399e2096f1a132c5'),  # supply    102.92 DAI and get same amount of aDAI  # noqa: E501
        deserialize_evm_tx_hash('0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60'),  # supply    160    DAI  # noqa: E501
        deserialize_evm_tx_hash('0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c'),  # supply    390    DAI  # noqa: E501
        deserialize_evm_tx_hash('0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc'),  # supply    58.985 DAI  # noqa: E501
        deserialize_evm_tx_hash('0x07ac09cc06c7cd74c7312f3a82c9f77d69ba7a89a4a3b7ded33db07e32c3607c'),  # cast vote interest update  # noqa: E501
        deserialize_evm_tx_hash('0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871'),  # supply    168.84 DAI  # noqa: E501
        deserialize_evm_tx_hash('0xc3a8978418afa1a4f139e9314ac787cacfbed79b1daa28e146bb0bf6fdf79a41'),  # supply    1939.8 DAI  # noqa: E501
        deserialize_evm_tx_hash('0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410'),  # supply    2507.6 DAI  # noqa: E501
        deserialize_evm_tx_hash('0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486'),  # withdraw  7968.4 DAI  # noqa: E501
    ]
    with patch_decoder_reload_data():
        ethereum_transaction_decoder.decode_transaction_hashes(
            ignore_cache=True,
            tx_hashes=tx_hashes,
        )

    aave = Aave(
        ethereum_inquirer=node_inquirer,
        database=database,
        premium=rotkehlchen_api_server.rest_api.rotkehlchen.premium,
        msg_aggregator=rotkehlchen_api_server.rest_api.rotkehlchen.msg_aggregator,
    )
    aave.get_stats_for_addresses(
        addresses=['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'],
        from_timestamp=Timestamp(0),
        to_timestamp=ts_now(),
        aave_balances=AaveBalances({}, {}),
    )
