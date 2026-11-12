from unittest.mock import MagicMock, patch

from rotkehlchen.accounting.structures.balance import Balance, ClaimEntry
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.ethena.balances import EthenaBalances
from rotkehlchen.chain.ethereum.modules.ethena.constants import (
    CPT_ETHENA,
    ETHENA_STAKING_ABI,
    SENA_ADDRESS,
    STAKING_VAULTS,
    SUSDE_ADDRESS,
)
from rotkehlchen.chain.evm.contracts import WEB3, EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, Timestamp

A_USDE = Asset(STAKING_VAULTS[SUSDE_ADDRESS].underlying_token_id)
A_ENA = Asset(STAKING_VAULTS[SENA_ADDRESS].underlying_token_id)


def _returned(vault_address: ChecksumEvmAddress) -> MagicMock:
    """An event returning the staked tokens of the given vault"""
    return MagicMock(asset=Asset(STAKING_VAULTS[vault_address].token_id))


def _cooldowns_call(
        vault_address: ChecksumEvmAddress,
        address: ChecksumEvmAddress,
) -> tuple[ChecksumEvmAddress, str]:
    return vault_address, EvmContract(
        address=vault_address,
        abi=ETHENA_STAKING_ABI,
        deployed_block=0,
    ).encode(method_name='cooldowns', arguments=[address])


def test_ethena_cooldown_balances() -> None:
    inquirer = MagicMock()
    addresses = [string_to_evm_address(f'0x{i:040x}') for i in range(1, 4)]
    inquirer.multicall.return_value = [
        WEB3.codec.encode(['uint104', 'uint152'], [1794500000, 2 * 10**18]),  # 1st sUSDe
        WEB3.codec.encode(['uint104', 'uint152'], [1795000000, 3 * 10**18]),  # 2nd sENA
        WEB3.codec.encode(['uint104', 'uint152'], [1794000000, 5 * 10**18]),  # 2nd sUSDe
        WEB3.codec.encode(['uint104', 'uint152'], [0, 0]),  # 3rd sUSDe, already unstaked
    ]
    protocol = EthenaBalances(evm_inquirer=inquirer, tx_decoder=MagicMock())
    with (
        patch.object(protocol, 'addresses_with_deposits', return_value={
            # an event edited by the user can have the counterparty without returning a vault token
            addresses[0]: [_returned(SUSDE_ADDRESS), _returned(SUSDE_ADDRESS), MagicMock(asset=A_USDE)],  # noqa: E501
            addresses[1]: [_returned(SENA_ADDRESS), _returned(SUSDE_ADDRESS)],
            addresses[2]: [_returned(SUSDE_ADDRESS)],
        }),
        patch(
            'rotkehlchen.chain.ethereum.modules.ethena.balances.Inquirer.find_main_currency_prices',
            return_value={A_USDE: FVal(1), A_ENA: FVal('0.5')},
        ),
    ):
        balances = protocol.query_balances(addresses)

    # one call per vault the address returned staked tokens to, even after several cooldowns
    assert inquirer.multicall.call_args.kwargs['calls'] == [
        _cooldowns_call(SUSDE_ADDRESS, addresses[0]),
        _cooldowns_call(SENA_ADDRESS, addresses[1]),
        _cooldowns_call(SUSDE_ADDRESS, addresses[1]),
        _cooldowns_call(SUSDE_ADDRESS, addresses[2]),
    ]
    assert balances[addresses[0]].assets[A_USDE][CPT_ETHENA] == Balance(
        amount=FVal(2),
        value=FVal(2),
        awaiting_claim=FVal(2),
        claims=(ClaimEntry(amount=FVal(2), available_at=Timestamp(1794500000)),),
    )
    assert balances[addresses[1]].assets[A_ENA][CPT_ETHENA] == Balance(
        amount=FVal(3),
        value=FVal('1.5'),
        awaiting_claim=FVal(3),
        claims=(ClaimEntry(amount=FVal(3), available_at=Timestamp(1795000000)),),
    )
    assert balances[addresses[1]].assets[A_USDE][CPT_ETHENA] == Balance(
        amount=FVal(5),
        value=FVal(5),
        awaiting_claim=FVal(5),
        claims=(ClaimEntry(amount=FVal(5), available_at=Timestamp(1794000000)),),
    )
    assert addresses[2] not in balances


def test_ethena_skips_rpc_without_cooldowns() -> None:
    inquirer = MagicMock()
    protocol = EthenaBalances(evm_inquirer=inquirer, tx_decoder=MagicMock())
    with patch.object(protocol, 'addresses_with_deposits', return_value={}):
        assert len(protocol.query_balances([string_to_evm_address(f'0x{1:040x}')])) == 0
    inquirer.multicall.assert_not_called()


def test_ethena_cooldown_query_failure() -> None:
    inquirer = MagicMock()
    inquirer.multicall.side_effect = RemoteError('node is down', cause=FailureCause.NETWORK)
    protocol = EthenaBalances(evm_inquirer=inquirer, tx_decoder=MagicMock())
    with patch.object(protocol, 'addresses_with_deposits', return_value={
        (address := string_to_evm_address(f'0x{1:040x}')): [_returned(SUSDE_ADDRESS)],
    }):
        assert len(protocol.query_balances([address])) == 0
