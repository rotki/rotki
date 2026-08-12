from unittest.mock import MagicMock

from rotkehlchen.chain.aggregator import CHAIN_TO_BALANCE_PROTOCOLS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.frankencoin.savings.balances import (
    FrankencoinSavingsBalances,
)
from rotkehlchen.chain.evm.decoding.frankencoin.savings.constants import (
    SUPPORTED_ZCHF_SAVINGS_CHAINS,
)
from rotkehlchen.constants.assets import A_ZCHF
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address


def test_frankencoin_savings_balances_registration():
    for chain_id in SUPPORTED_ZCHF_SAVINGS_CHAINS:
        assert FrankencoinSavingsBalances in CHAIN_TO_BALANCE_PROTOCOLS[chain_id]


def _make_balances_module(addresses):
    module = object.__new__(FrankencoinSavingsBalances)
    module.evm_inquirer = MagicMock(chain_name='ethereum')
    module.addresses_with_deposits = MagicMock(return_value={address: [] for address in addresses})
    module._add_priced_balances = MagicMock()
    module.savings_contract = MagicMock(address=make_evm_address())
    return module


def test_query_frankencoin_savings_balances():
    addresses = [make_evm_address(), make_evm_address()]
    module = _make_balances_module(addresses)
    module.savings_contract.encode.side_effect = [
        'savings-0', 'interest-0', 'savings-1', 'interest-1',
    ]
    module.savings_contract.decode.side_effect = [
        (10**18, 0, make_evm_address(), 0),
        (25 * 10**16,),
        (0, 0, make_evm_address(), 0),
        (0,),
    ]
    module.evm_inquirer.multicall.return_value = [b'1', b'2', b'3', b'4']

    balances = module.query_balances()

    assert module.evm_inquirer.multicall.call_args.kwargs['calls'] == [
        (module.savings_contract.address, 'savings-0'),
        (module.savings_contract.address, 'interest-0'),
        (module.savings_contract.address, 'savings-1'),
        (module.savings_contract.address, 'interest-1'),
    ]
    module._add_priced_balances.assert_called_once_with(
        balances=balances,
        amounts=[(addresses[0], A_ZCHF, FVal('1.25'))],
    )


def test_query_frankencoin_savings_balances_deducts_pending_referral_fee():
    module = _make_balances_module(addresses := [make_evm_address()])
    module.savings_contract.decode.side_effect = [
        (10**18, 0, make_evm_address(), 250_000),
        (4 * 10**17,),
    ]
    module.evm_inquirer.multicall.return_value = [b'1', b'2']

    balances = module.query_balances()

    module._add_priced_balances.assert_called_once_with(
        balances=balances,
        amounts=[(addresses[0], A_ZCHF, FVal('1.3'))],
    )


def test_query_frankencoin_savings_balances_ignores_fee_without_referrer():
    module = _make_balances_module(addresses := [make_evm_address()])
    module.savings_contract.decode.side_effect = [
        (10**18, 0, ZERO_ADDRESS, 250_000),
        (4 * 10**17,),
    ]
    module.evm_inquirer.multicall.return_value = [b'1', b'2']

    balances = module.query_balances()

    module._add_priced_balances.assert_called_once_with(
        balances=balances,
        amounts=[(addresses[0], A_ZCHF, FVal('1.4'))],
    )


def test_query_frankencoin_savings_balances_without_depositors():
    module = _make_balances_module([])

    assert module.query_balances() == {}
    module.evm_inquirer.multicall.assert_not_called()
    module._add_priced_balances.assert_not_called()


def test_query_frankencoin_savings_balances_remote_error():
    module = _make_balances_module([make_evm_address()])
    module.evm_inquirer.multicall.side_effect = RemoteError('RPC unavailable')

    assert module.query_balances() == {}

    module._add_priced_balances.assert_not_called()


def test_query_frankencoin_savings_balances_empty_multicall():
    module = _make_balances_module([make_evm_address()])
    module.evm_inquirer.multicall.return_value = []

    assert module.query_balances() == {}
    module._add_priced_balances.assert_not_called()


def test_query_frankencoin_savings_balances_decode_error():
    module = _make_balances_module([make_evm_address()])
    module.evm_inquirer.multicall.return_value = [b'1', b'2']
    module.savings_contract.decode.side_effect = DeserializationError('invalid response')

    assert module.query_balances() == {}
