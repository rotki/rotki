from contextlib import ExitStack
from unittest.mock import patch

import pytest

from rotkehlchen.chain.aggregator import _module_name_to_class
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import AVAILABLE_MODULES_MAP, SupportedBlockchain


@pytest.mark.parametrize('ethereum_modules', [[]])
def test_module_activation(blockchain):
    for module_name in AVAILABLE_MODULES_MAP:
        expected_module_type = _module_name_to_class(module_name)
        module = blockchain.activate_module(module_name)
        assert isinstance(module, expected_module_type)
        assert blockchain.eth_modules[module_name] == module


@pytest.mark.parametrize('ethereum_modules', [AVAILABLE_MODULES_MAP.keys()])
def test_module_deactivation(blockchain):
    for module_name in AVAILABLE_MODULES_MAP:
        expected_module_type = _module_name_to_class(module_name)
        assert isinstance(blockchain.eth_modules[module_name], expected_module_type)
        blockchain.deactivate_module(module_name)
        assert module_name not in blockchain.eth_modules


def test_filter_active_evm_addresses(blockchain):

    contract_addy = make_evm_address()
    all_addy = make_evm_address()
    optimism_addy = make_evm_address()
    avalanche_addy = make_evm_address()

    def mock_ethereum_get_code(account):
        if account == contract_addy:
            return '0xsomecode'
        return '0x'

    def mock_avax_get_tx_count(account):
        if account in (all_addy, avalanche_addy):
            return 1
        return 0

    def mock_avax_balance(account):
        if account in (all_addy, avalanche_addy):
            return FVal(1)
        return ZERO

    def mock_optimism_has_activity(account):
        if account in (all_addy, optimism_addy):
            return True
        return False

    with ExitStack() as stack:
        stack.enter_context(patch.object(
            blockchain.ethereum.node_inquirer,
            'get_code',
            side_effect=mock_ethereum_get_code,
        ))
        stack.enter_context(patch.object(
            blockchain.avalanche.w3.eth,
            'get_transaction_count',
            side_effect=mock_avax_get_tx_count,
        ))
        stack.enter_context(patch.object(
            blockchain.avalanche,
            'get_avax_balance',
            side_effect=mock_avax_balance,
        ))
        stack.enter_context(patch.object(
            blockchain.optimism.node_inquirer.etherscan,
            'has_activity',
            side_effect=mock_optimism_has_activity,
        ))

        assert set(blockchain.filter_active_evm_addresses([contract_addy])) == {
            (SupportedBlockchain.ETHEREUM, contract_addy),
        }
        assert set(blockchain.filter_active_evm_addresses([all_addy])) == {
            (SupportedBlockchain.ETHEREUM, all_addy),
            (SupportedBlockchain.AVALANCHE, all_addy),
            (SupportedBlockchain.OPTIMISM, all_addy),
        }
        assert set(blockchain.filter_active_evm_addresses([avalanche_addy])) == {
            (SupportedBlockchain.ETHEREUM, avalanche_addy),
            (SupportedBlockchain.AVALANCHE, avalanche_addy),
        }
        assert set(blockchain.filter_active_evm_addresses([optimism_addy])) == {
            (SupportedBlockchain.ETHEREUM, optimism_addy),
            (SupportedBlockchain.OPTIMISM, optimism_addy),
        }
        assert set(blockchain.filter_active_evm_addresses([optimism_addy, all_addy, contract_addy])) == {  # noqa: E501
            (SupportedBlockchain.ETHEREUM, contract_addy),
            (SupportedBlockchain.ETHEREUM, all_addy),
            (SupportedBlockchain.AVALANCHE, all_addy),
            (SupportedBlockchain.OPTIMISM, all_addy),
            (SupportedBlockchain.ETHEREUM, optimism_addy),
            (SupportedBlockchain.OPTIMISM, optimism_addy),
        }
