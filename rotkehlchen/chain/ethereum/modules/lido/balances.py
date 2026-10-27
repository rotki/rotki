import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet, ClaimEntry
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_STETH
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

from .constants import CPT_LIDO, WITHDRAWAL_QUEUE

if TYPE_CHECKING:
    from eth_typing.abi import ABI

    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

WITHDRAWAL_QUEUE_ABI: Final[ABI] = [
    {'type': 'function', 'name': 'getWithdrawalRequests', 'stateMutability': 'view',
     'inputs': [{'name': '_owner', 'type': 'address'}],
     'outputs': [{'name': '', 'type': 'uint256[]'}]},
    {'type': 'function', 'name': 'getWithdrawalStatus', 'stateMutability': 'view',
     'inputs': [{'name': '_requestIds', 'type': 'uint256[]'}],
     'outputs': [{'name': '', 'type': 'tuple[]', 'components': [
         {'name': 'amountOfStETH', 'type': 'uint256'},
         {'name': 'amountOfShares', 'type': 'uint256'},
         {'name': 'owner', 'type': 'address'},
         {'name': 'timestamp', 'type': 'uint256'},
         {'name': 'isFinalized', 'type': 'bool'},
         {'name': 'isClaimed', 'type': 'bool'},
     ]}]},
    {'type': 'function', 'name': 'getLastCheckpointIndex', 'stateMutability': 'view',
     'inputs': [], 'outputs': [{'name': '', 'type': 'uint256'}]},
    {'type': 'function', 'name': 'findCheckpointHints', 'stateMutability': 'view',
     'inputs': [{'name': '_requestIds', 'type': 'uint256[]'},
                {'name': '_firstIndex', 'type': 'uint256'},
                {'name': '_lastIndex', 'type': 'uint256'}],
     'outputs': [{'name': '', 'type': 'uint256[]'}]},
    {'type': 'function', 'name': 'getClaimableEther', 'stateMutability': 'view',
     'inputs': [{'name': '_requestIds', 'type': 'uint256[]'},
                {'name': '_hints', 'type': 'uint256[]'}],
     'outputs': [{'name': '', 'type': 'uint256[]'}]},
]
STETH_SHARES_ABI: Final[ABI] = [{
    'type': 'function', 'name': 'getPooledEthByShares', 'stateMutability': 'view',
    'inputs': [{'name': '_sharesAmount', 'type': 'uint256'}],
    'outputs': [{'name': '', 'type': 'uint256'}],
}]


class LidoBalances(ProtocolWithBalance):
    """Value outstanding withdrawal NFTs by their current owner's queue requests."""

    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EthereumTransactionDecoder,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_LIDO,
            deposit_event_types=set(),
        )
        self.queue = EvmContract(
            address=WITHDRAWAL_QUEUE,
            abi=WITHDRAWAL_QUEUE_ABI,
            deployed_block=0,
        )
        self.steth = EvmContract(
            address=A_STETH.resolve_to_evm_token().evm_address,
            abi=STETH_SHARES_ABI,
            deployed_block=0,
        )

    def _withdrawal_claims(self, address: ChecksumEvmAddress) -> list[ClaimEntry]:
        """Return the unclaimed withdrawal requests currently owned by address.

        Finalized requests use the actual reserved ETH. For unfinalized requests the
        redeemable amount is capped at the original stETH, but can fall if shares lose
        value before finalization. Requests already claimed or transferred are excluded.
        """
        request_ids = self.queue.call(
            node_inquirer=self.evm_inquirer,
            method_name='getWithdrawalRequests',
            arguments=[address],
        )
        if not request_ids:
            return []

        statuses = self.queue.call(
            node_inquirer=self.evm_inquirer,
            method_name='getWithdrawalStatus',
            arguments=[request_ids],
        )
        finalized: list[tuple[int, int]] = []
        claims: list[ClaimEntry] = []
        for request_id, status in zip(request_ids, statuses, strict=True):
            steth_amount, shares, owner, requested_at, is_finalized, is_claimed = status
            if is_claimed or owner.lower() != address.lower():
                continue
            if is_finalized:
                finalized.append((request_id, requested_at))
                continue

            share_value = self.steth.call(
                node_inquirer=self.evm_inquirer,
                method_name='getPooledEthByShares',
                arguments=[shares],
            )
            claims.append(ClaimEntry(
                amount=token_normalized_value_decimals(min(steth_amount, share_value), 18),
                request_id=str(request_id),
                requested_at=Timestamp(requested_at),
            ))

        if finalized:
            finalized_ids = [request_id for request_id, _ in finalized]
            last_checkpoint = self.queue.call(
                node_inquirer=self.evm_inquirer,
                method_name='getLastCheckpointIndex',
            )
            hints = self.queue.call(
                node_inquirer=self.evm_inquirer,
                method_name='findCheckpointHints',
                arguments=[finalized_ids, 1, last_checkpoint],
            )
            payouts = self.queue.call(
                node_inquirer=self.evm_inquirer,
                method_name='getClaimableEther',
                arguments=[finalized_ids, hints],
            )
            claims.extend(ClaimEntry(
                amount=token_normalized_value_decimals(payout, 18),
                request_id=str(request_id),
                finalized=True,
                requested_at=Timestamp(requested_at),
            ) for (request_id, requested_at), payout in zip(finalized, payouts, strict=True))

        return claims

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        address_claims: dict[ChecksumEvmAddress, list[ClaimEntry]] = {}
        for address in addresses:
            try:
                claims = self._withdrawal_claims(address)
            except RemoteError as e:
                log.error(f'Failed to query Lido withdrawal queue for {address}: {e}')
                continue
            if len(claims) != 0:
                address_claims[address] = claims

        if len(address_claims) == 0:
            return balances
        price = Inquirer.find_price(from_asset=A_ETH, to_asset=CachedSettings().main_currency)
        for address, claims in address_claims.items():
            amount = sum((claim.amount for claim in claims), ZERO)
            balances[address].assets[A_ETH][self.counterparty] += Balance(
                amount=amount,
                value=amount * price,
                awaiting_claim=amount,
                claims=tuple(claims),
            )
        return balances
