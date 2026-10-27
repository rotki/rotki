import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet, ClaimEntry
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_STETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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
            deposit_event_types={(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED)},
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

    def _multicall(
            self,
            contract: EvmContract,
            method_name: str,
            arguments: list[list[Any]],
    ) -> list[tuple[Any, ...]]:
        """Call method_name once per arguments entry in a single multicall and decode each result.

        May raise:
            RemoteError: If the multicall fails.
            DeserializationError: If a result cannot be decoded.
        """
        results = self.evm_inquirer.multicall(calls=[
            (contract.address, contract.encode(method_name=method_name, arguments=args))
            for args in arguments
        ])
        return [
            contract.decode(result=result, method_name=method_name, arguments=args)
            for args, result in zip(arguments, results, strict=True)
        ]

    def _withdrawal_claims(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list[ClaimEntry]]:
        """Return the unclaimed withdrawal requests currently owned by each address.

        Finalized requests use the actual reserved ETH. For unfinalized requests the
        redeemable amount is capped at the original stETH, but can fall if shares lose
        value before finalization. Requests already claimed or transferred are excluded.
        """
        request_ids = [ids for (ids,) in self._multicall(
            contract=self.queue,
            method_name='getWithdrawalRequests',
            arguments=[[address] for address in addresses],
        )]
        owners_with_requests = [
            (address, list(ids)) for address, ids in zip(addresses, request_ids, strict=True)
            if len(ids) != 0
        ]
        if len(owners_with_requests) == 0:
            return {}

        statuses = self._multicall(
            contract=self.queue,
            method_name='getWithdrawalStatus',
            arguments=[[ids] for _, ids in owners_with_requests],
        )
        pending: list[tuple[ChecksumEvmAddress, int, int, int, int]] = []
        finalized: dict[ChecksumEvmAddress, list[tuple[int, int]]] = defaultdict(list)
        for (address, ids), (address_statuses,) in zip(owners_with_requests, statuses, strict=True):  # noqa: E501
            for request_id, status in zip(ids, address_statuses, strict=True):
                steth_amount, shares, owner, requested_at, is_finalized, is_claimed = status
                if is_claimed or owner.lower() != address.lower():
                    continue
                if is_finalized:
                    finalized[address].append((request_id, requested_at))
                else:
                    pending.append((address, request_id, steth_amount, shares, requested_at))

        claims: dict[ChecksumEvmAddress, list[ClaimEntry]] = defaultdict(list)
        if len(pending) != 0:
            share_values = self._multicall(
                contract=self.steth,
                method_name='getPooledEthByShares',
                arguments=[[shares] for _, _, _, shares, _ in pending],
            )
            for (address, request_id, steth_amount, _, requested_at), (share_value,) in zip(pending, share_values, strict=True):  # noqa: E501
                claims[address].append(ClaimEntry(
                    amount=token_normalized_value_decimals(min(steth_amount, share_value), 18),
                    request_id=str(request_id),
                    requested_at=Timestamp(requested_at),
                ))

        if len(finalized) != 0:
            finalized_ids = {
                address: [request_id for request_id, _ in entries]
                for address, entries in finalized.items()
            }
            ((last_checkpoint,),) = self._multicall(
                contract=self.queue,
                method_name='getLastCheckpointIndex',
                arguments=[[]],
            )
            hints = self._multicall(
                contract=self.queue,
                method_name='findCheckpointHints',
                arguments=[[ids, 1, last_checkpoint] for ids in finalized_ids.values()],
            )
            payouts = self._multicall(
                contract=self.queue,
                method_name='getClaimableEther',
                arguments=[
                    [ids, address_hints]
                    for ids, (address_hints,) in zip(finalized_ids.values(), hints, strict=True)
                ],
            )
            for (address, entries), (address_payouts,) in zip(finalized.items(), payouts, strict=True):  # noqa: E501
                claims[address].extend(ClaimEntry(
                    amount=token_normalized_value_decimals(payout, 18),
                    request_id=str(request_id),
                    finalized=True,
                    requested_at=Timestamp(requested_at),
                ) for (request_id, requested_at), payout in zip(entries, address_payouts, strict=True))  # noqa: E501

        return claims

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(owners := list(self.addresses_with_deposits(location_labels=addresses))) == 0:
            return balances

        try:
            address_claims = self._withdrawal_claims(owners)
        except (RemoteError, DeserializationError) as e:
            log.error('Failed to query Lido withdrawal queue: %s', e)
            return balances

        if len(address_claims) == 0:
            return balances
        price = Inquirer.find_main_currency_price(A_ETH)
        for address, claims in address_claims.items():
            amount = sum((claim.amount for claim in claims), ZERO)
            balances[address].assets[A_ETH][self.counterparty] += Balance(
                amount=amount,
                value=amount * price,
                awaiting_claim=amount,
                claims=tuple(claims),
            )
        return balances
