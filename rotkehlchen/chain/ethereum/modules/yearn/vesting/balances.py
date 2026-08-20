import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address

from .constants import CPT_YEARN_VESTING, VESTING_ESCROW_ABI, VYPER_DONATION_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
VESTING_BALANCE_METHODS: Final = ('recipient', 'start_time', 'end_time', 'cliff_length', 'disabled_at', 'total_locked', 'total_claimed')  # noqa: E501


def vested_amount_at(
        timestamp: int,
        start_time: int,
        end_time: int,
        cliff_length: int,
        total_locked: int,
) -> int:
    """Calculate the raw token amount vested at the given timestamp
    following the linear vesting schedule of the escrows.
    """
    if timestamp < start_time + cliff_length:
        return 0
    if timestamp >= end_time:
        return total_locked

    return total_locked * (timestamp - start_time) // (end_time - start_time)


class YearnVestingBalances(ProtocolWithBalance):
    """Query the tokens still owed by yearn vesting escrows to tracked recipients.

    The escrows are discovered from the already decoded vesting events (either the
    funding deposit or a claim), and the remaining balance (locked + unclaimed) is
    computed from the escrow's vesting schedule instead of its token balance, so
    that tokens donated to an escrow by a third party are not counted.
    """

    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EthereumTransactionDecoder,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_YEARN_VESTING,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},  # noqa: E501
        )

    def query_balances(self, addresses: list[ChecksumEvmAddress]) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        addresses_to_events = self.addresses_with_activity(
            event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
                (HistoryEventType.WITHDRAWAL, HistoryEventSubType.WITHDRAW_FROM_PROTOCOL),
            },
            location_labels=addresses,
        )
        escrow_to_token: dict[ChecksumEvmAddress, EvmToken] = {}
        for events in addresses_to_events.values():
            for event in events:
                if event.address is not None and event.address != VYPER_DONATION_ADDRESS:
                    escrow_to_token[event.address] = event.asset.resolve_to_evm_token()

        if len(escrow_to_token) == 0:
            return balances

        queried_addresses = set(addresses)

        escrow_contract = EvmContract(  # only used to encode/decode, the calls carry the address
            address=(escrows := list(escrow_to_token))[0],
            abi=VESTING_ESCROW_ABI,
            deployed_block=0,
        )
        try:
            results = self.evm_inquirer.multicall(calls=[
                (escrow, escrow_contract.encode(method_name=method))
                for escrow in escrows
                for method in VESTING_BALANCE_METHODS
            ])
        except RemoteError as e:
            log.error('Failed to query yearn vesting escrow balances via multicall due to %s', e)
            return balances

        amounts = []
        for idx, escrow in enumerate(escrows):
            decoded = [escrow_contract.decode(
                result=results[idx * len(VESTING_BALANCE_METHODS) + method_idx],
                method_name=method,
            )[0] for method_idx, method in enumerate(VESTING_BALANCE_METHODS)]
            if (recipient := deserialize_evm_address(decoded[0])) not in queried_addresses:
                continue  # the queried address only funded the escrow of another recipient

            _, start_time, end_time, cliff_length, disabled_at, total_locked, total_claimed = decoded  # noqa: E501
            raw_remaining = vested_amount_at(
                # a revocation stops vesting at disabled_at. Active escrows hold
                # 0 (v0.4.0) or end_time (older versions) there
                timestamp=end_time if disabled_at in (0, end_time) else disabled_at,
                start_time=start_time,
                end_time=end_time,
                cliff_length=cliff_length,
                total_locked=total_locked,
            ) - total_claimed
            if raw_remaining <= 0:
                continue  # fully claimed or revoked escrow

            token = escrow_to_token[escrow]
            amounts.append((recipient, token, token_normalized_value(
                token_amount=raw_remaining,
                token=token,
            )))

        self._add_priced_balances(balances=balances, amounts=amounts)
        return balances
