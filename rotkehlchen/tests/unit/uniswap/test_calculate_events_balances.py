from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
    get_decoded_events_of_transaction,
)

from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

from .utils import (
    TEST_ADDRESS_1,
    const_lp_1_events_balance,
    const_lp_2_events_balance,
    const_lp_3_balance,
    const_lp_3_events_balance,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_no_events_no_balances(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    uniswap = rotki.chains_aggregator.get_module('uniswap')
    assert uniswap is not None
    events_balances = uniswap.get_balances_chain(addresses=[TEST_ADDRESS_1])
    assert events_balances == {}


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0x6C0F75eb3D69B9Ea2fB88dbC37fc086a12bBC93F']])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize(*ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
def test_single_pool_without_balances(rotkehlchen_api_server: 'APIServer', ethereum_accounts):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    ethereum_inquirer = rotki.chains_aggregator.ethereum.node_inquirer
    uniswap = rotki.chains_aggregator.get_module('uniswap')
    tx_hex_1 = deserialize_evm_tx_hash('0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824')  # noqa: E501
    tx_hex_2 = deserialize_evm_tx_hash('0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa')  # noqa: E501
    for tx_hex in (tx_hex_1, tx_hex_2):
        get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            database=database,
            tx_hash=tx_hex,
        )
    assert uniswap is not None
    with patch(
        'rotkehlchen.chain.ethereum.modules.uniswap.uniswap.Uniswap.get_balances',
        side_effect=lambda _: {},
    ):
        events_balances = uniswap.get_stats_for_addresses(
            addresses=[ethereum_accounts[0]],
            from_timestamp=Timestamp(0),
            to_timestamp=ts_now(),
        )
    assert events_balances[ethereum_accounts[0]] == [const_lp_1_events_balance()]


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0x6C0F75eb3D69B9Ea2fB88dbC37fc086a12bBC93F']])
@pytest.mark.parametrize('network_mocking', [False])
def test_multiple_pools_without_balances(rotkehlchen_api_server: 'APIServer', ethereum_accounts):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    ethereum_inquirer = rotki.chains_aggregator.ethereum.node_inquirer
    uniswap = rotki.chains_aggregator.get_module('uniswap')
    tx_hex_1 = deserialize_evm_tx_hash('0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824')  # noqa: E501
    tx_hex_2 = deserialize_evm_tx_hash('0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa')  # noqa: E501
    tx_hex_3 = deserialize_evm_tx_hash('0x1e7fd116b316af49f6c52b3ca44f3c5d24c2a6f80a5b5e674b5f94155bd2cec4')  # noqa: E501
    tx_hex_4 = deserialize_evm_tx_hash('0x140bdba831f9494cf0ead6d57009e1eae45ed629a78ee74ccbf49018afae0ffa')  # noqa: E501
    for tx_hex in (tx_hex_1, tx_hex_2, tx_hex_3, tx_hex_4):
        get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            database=database,
            tx_hash=tx_hex,
        )
    uniswap = rotki.chains_aggregator.get_module('uniswap')
    assert uniswap is not None
    with patch(
        'rotkehlchen.chain.ethereum.modules.uniswap.uniswap.Uniswap.get_balances',
        side_effect=lambda _: {},
    ):
        events_balances = uniswap.get_stats_for_addresses(
            addresses=[ethereum_accounts[0]],
            from_timestamp=Timestamp(0),
            to_timestamp=ts_now(),
        )
    assert events_balances[ethereum_accounts[0]] == [const_lp_2_events_balance(), const_lp_1_events_balance()]  # noqa: E501


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0x6C0F75eb3D69B9Ea2fB88dbC37fc086a12bBC93F']])
@pytest.mark.parametrize('network_mocking', [False])
def test_single_pool_with_balances(rotkehlchen_api_server: 'APIServer', ethereum_accounts):
    """Test LP current balances are factorized in the pool events balance
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    ethereum_inquirer = rotki.chains_aggregator.ethereum.node_inquirer
    tx_hex_1 = deserialize_evm_tx_hash('0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824')  # noqa: E501
    tx_hex_2 = deserialize_evm_tx_hash('0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa')  # noqa: E501
    for tx_hex in (tx_hex_1, tx_hex_2):
        get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            database=database,
            tx_hash=tx_hex,
        )
    uniswap = rotki.chains_aggregator.get_module('uniswap')
    assert uniswap is not None
    with patch(
        'rotkehlchen.chain.ethereum.modules.uniswap.uniswap.Uniswap.get_balances',
        side_effect=lambda _: {ethereum_accounts[0]: [const_lp_3_balance()]},
    ):
        events_balances = uniswap.get_stats_for_addresses(
            addresses=ethereum_accounts,
            from_timestamp=Timestamp(0),
            to_timestamp=ts_now(),
        )
    assert events_balances[ethereum_accounts[0]] == [const_lp_3_events_balance()]
