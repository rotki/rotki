import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from eth_typing.abi import ABI

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CPT_SAFE, SAFE_LOCKING, SAFE_TOKEN_ID, SAFENET_STAKING

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Minimal ABI of the SafeNet staking contract for the read methods we need. totalStakerStakes
# returns the amount actively staked across all validators, while getPendingWithdrawals returns
# the withdrawals that have been initiated but not yet claimed (still held by the contract).
SAFENET_STAKING_ABI: Final[ABI] = [
    {'inputs': [{'name': '', 'type': 'address'}], 'name': 'totalStakerStakes', 'outputs': [{'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'},  # noqa: E501
    {'inputs': [{'name': '', 'type': 'address'}], 'name': 'getPendingWithdrawals', 'outputs': [{'components': [{'name': 'amount', 'type': 'uint256'}, {'name': 'claimableAt', 'type': 'uint256'}], 'name': '', 'type': 'tuple[]'}], 'stateMutability': 'view', 'type': 'function'},  # noqa: E501
]


class SafeBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_SAFE,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},  # noqa: E501
        )

    def _query_locked_safe(
            self,
            addresses: list['ChecksumEvmAddress'],
            safe_asset: Asset,
    ) -> list[tuple['ChecksumEvmAddress', Asset, FVal]]:
        """Query the amount of SAFE locked in the safe locking contract for each address."""
        lock_contract = self.evm_inquirer.contracts.contract(SAFE_LOCKING)
        calls = [
            (
                lock_contract.address,
                lock_contract.encode(method_name='getUserTokenBalance', arguments=[user_address]),
            )
            for user_address in addresses
        ]
        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error('Failed to query locked SAFE balances due to %s', e)
            return []

        entries: list[tuple[ChecksumEvmAddress, Asset, FVal]] = []
        for idx, result in enumerate(results):
            amount = token_normalized_value_decimals(
                token_amount=lock_contract.decode(
                    result=result,
                    method_name='getUserTokenBalance',
                    arguments=[user_address := addresses[idx]],
                )[0],
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )
            if amount > ZERO:
                entries.append((user_address, safe_asset, amount))

        return entries

    def _query_safenet_staked(
            self,
            addresses: list['ChecksumEvmAddress'],
            safe_asset: Asset,
    ) -> list[tuple['ChecksumEvmAddress', Asset, FVal]]:
        """Query the amount of SAFE staked in SafeNet for each address. This includes both the
        actively staked amount and any initiated-but-unclaimed withdrawals, since both are still
        held by the staking contract on behalf of the staker."""
        staking_contract = EvmContract(
            address=SAFENET_STAKING,
            abi=SAFENET_STAKING_ABI,
            deployed_block=0,  # not used here
        )
        calls: list[tuple[ChecksumEvmAddress, str]] = []
        for user_address in addresses:
            calls.extend((
                (SAFENET_STAKING, staking_contract.encode(
                    method_name='totalStakerStakes', arguments=[user_address],
                )),
                (SAFENET_STAKING, staking_contract.encode(
                    method_name='getPendingWithdrawals', arguments=[user_address],
                )),
            ))

        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error('Failed to query staked SAFE balances due to %s', e)
            return []

        entries: list[tuple[ChecksumEvmAddress, Asset, FVal]] = []
        for idx, user_address in enumerate(addresses):
            raw_amount = staking_contract.decode(
                result=results[idx * 2],
                method_name='totalStakerStakes',
                arguments=[user_address],
            )[0] + sum(node[0] for node in staking_contract.decode(
                result=results[idx * 2 + 1],
                method_name='getPendingWithdrawals',
                arguments=[user_address],
            )[0])
            if raw_amount <= 0:
                continue

            entries.append((user_address, safe_asset, token_normalized_value_decimals(
                token_amount=raw_amount,
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )))

        return entries

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances of locked and SafeNet-staked SAFE tokens if deposit events are found."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        entries: list[tuple[ChecksumEvmAddress, Asset, FVal]] = []
        safe_asset = Asset(SAFE_TOKEN_ID)
        if len(locked := self.addresses_with_activity(
            event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},
        )) != 0:
            entries.extend(self._query_locked_safe(list(locked), safe_asset))

        if len(staked := self.addresses_with_activity(
            event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )) != 0:
            entries.extend(self._query_safenet_staked(list(staked), safe_asset))

        self._add_priced_balances(balances=balances, amounts=entries)
        return balances
