from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.chainlink.balances import ChainlinkBalances
from rotkehlchen.chain.ethereum.modules.chainlink.constants import (
    CHAINLINK_STAKING_ABI,
    COMMUNITY_POOL,
    CPT_CHAINLINK,
    OPERATOR_POOL,
    REWARD_VAULT,
    STAKING_V01,
)
from rotkehlchen.chain.evm.contracts import WEB3, EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_LINK
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress

CONTRACT = EvmContract(address=COMMUNITY_POOL, abi=CHAINLINK_STAKING_ABI)


def _staked_in(address: ChecksumEvmAddress) -> MagicMock:
    """A staking deposit event to the given staking contract"""
    return MagicMock(address=address)


def _calls(
        address: ChecksumEvmAddress,
        with_v01: bool,
) -> list[tuple[ChecksumEvmAddress, str]]:
    calls = [
        (COMMUNITY_POOL, 'getStakerPrincipal'),
        (OPERATOR_POOL, 'getStakerPrincipal'),
        (REWARD_VAULT, 'getReward'),
    ]
    if with_v01:
        calls.extend((
            (STAKING_V01, 'getStake'),
            (STAKING_V01, 'getBaseReward'),
            (STAKING_V01, 'getDelegationReward'),
        ))
    return [
        (contract_address, CONTRACT.encode(method_name=method, arguments=[address]))
        for contract_address, method in calls
    ]


def _results(*amounts: str) -> list[bytes]:
    return [WEB3.codec.encode(['uint256'], [(FVal(amount) * 10**18).to_int(exact=True)]) for amount in amounts]  # noqa: E501


def test_chainlink_staking_balances() -> None:
    inquirer = MagicMock()
    addresses = [string_to_evm_address(f'0x{i:040x}') for i in range(1, 5)]
    inquirer.multicall.return_value = [
        *_results('100', '0', '2.5'),  # 1st staked in the community pool
        *_results('1000', '0', '4', '50', '1', '0.5'),  # 2nd staked in v0.1 and then in v0.2
        *_results('0', '0', '0', '0', '0', '0'),  # 3rd unstaked from v0.1
        *_results('0', '0', '0.25'),  # 4th unstaked but has not claimed all its rewards
    ]
    protocol = ChainlinkBalances(evm_inquirer=inquirer, tx_decoder=MagicMock())
    with (
        patch.object(protocol, 'addresses_with_deposits', return_value={
            addresses[0]: [_staked_in(COMMUNITY_POOL), _staked_in(COMMUNITY_POOL)],
            addresses[1]: [_staked_in(STAKING_V01), _staked_in(COMMUNITY_POOL)],
            addresses[2]: [_staked_in(STAKING_V01)],
            addresses[3]: [_staked_in(COMMUNITY_POOL)],
        }),
        patch(
            'rotkehlchen.chain.ethereum.interfaces.balances.Inquirer.find_main_currency_prices',
            return_value={A_LINK: FVal(10)},
        ),
    ):
        balances = protocol.query_balances(addresses)

    # v0.1 is only queried for the addresses that staked there
    assert inquirer.multicall.call_args.kwargs['calls'] == [
        *_calls(addresses[0], with_v01=False),
        *_calls(addresses[1], with_v01=True),
        *_calls(addresses[2], with_v01=True),
        *_calls(addresses[3], with_v01=False),
    ]
    assert balances[addresses[0]].assets[A_LINK][CPT_CHAINLINK] == Balance(
        amount=FVal('102.5'),
        value=FVal(1025),
    )
    assert balances[addresses[1]].assets[A_LINK][CPT_CHAINLINK] == Balance(
        amount=FVal('1055.5'),
        value=FVal(10555),
    )
    assert addresses[2] not in balances
    assert balances[addresses[3]].assets[A_LINK][CPT_CHAINLINK] == Balance(
        amount=FVal('0.25'),
        value=FVal('2.5'),
    )


def test_chainlink_skips_rpc_without_stakes() -> None:
    inquirer = MagicMock()
    protocol = ChainlinkBalances(evm_inquirer=inquirer, tx_decoder=MagicMock())
    with patch.object(protocol, 'addresses_with_deposits', return_value={}):
        assert len(protocol.query_balances([string_to_evm_address(f'0x{1:040x}')])) == 0
    inquirer.multicall.assert_not_called()


def test_chainlink_staking_query_failure() -> None:
    inquirer = MagicMock()
    inquirer.multicall.side_effect = RemoteError('node is down', cause=FailureCause.NETWORK)
    protocol = ChainlinkBalances(evm_inquirer=inquirer, tx_decoder=MagicMock())
    with patch.object(protocol, 'addresses_with_deposits', return_value={
        (address := string_to_evm_address(f'0x{1:040x}')): [_staked_in(COMMUNITY_POOL)],
    }):
        assert len(protocol.query_balances([address])) == 0
