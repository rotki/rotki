import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import (
    CPT_ONEINCH_LIQUIDITY,
    DEPOSITED,
    ONEINCH_LIQUIDITY_CPT_DETAILS,
    ONEINCH_LIQUIDITY_LABEL,
    WITHDRAWN,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OneinchliquidityDecoder(EvmDecoderInterface):
    """Decoder for the Mooniswap and 1inch Liquidity Protocol pools.

    The pools are deployed by a factory so their addresses are not known in advance. The LP
    token of a pool is the pool contract itself, so a mint or burn of a token whose contract
    also emitted a Deposited/Withdrawn log in the same transaction identifies the pool. That
    check happens in a transfer enricher, which only runs for transfers of tracked addresses,
    and the actual event processing happens in a post-decoding rule.
    """

    @staticmethod
    def _find_pool_logs(
            all_logs: list[EvmTxReceiptLog],
            pool_address: ChecksumEvmAddress | None = None,
    ) -> list[EvmTxReceiptLog]:
        """Return the Deposited/Withdrawn logs of the transaction, optionally only for one pool"""
        return [
            tx_log for tx_log in all_logs
            if (
                len(tx_log.topics) == 3 and
                tx_log.topics[0] in (DEPOSITED, WITHDRAWN) and
                (pool_address is None or tx_log.address == pool_address)
            )
        ]

    def _maybe_enrich_pool_token_transfer(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """Match the mint or burn of a pool's LP token to trigger the post decoding rule"""
        if (
            context.event.address != ZERO_ADDRESS or
            len(self._find_pool_logs(context.all_logs, pool_address=context.tx_log.address)) == 0
        ):
            return FAILED_ENRICHMENT_OUTPUT

        return TransferEnrichmentOutput(matched_counterparty=CPT_ONEINCH_LIQUIDITY)

    def _process_deposit(
            self,
            pool_address: ChecksumEvmAddress,
            decoded_events: list[EvmEvent],
    ) -> bool:
        """Turn the transfers of a pool deposit into deposit and receive wrapped events.

        The pool refunds any ETH sent in excess of what it needed, so a receive of ETH
        from the pool is marked as a refund. Returns whether the events were found.
        """
        deposit_events, receive_events = [], []
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == pool_address
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_ONEINCH_LIQUIDITY
                event.notes = f'Deposit {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} to {ONEINCH_LIQUIDITY_LABEL} pool {pool_address}'  # noqa: E501
                deposit_events.append(event)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS and
                event.asset.identifier.endswith(pool_address)  # the pool's own token
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_ONEINCH_LIQUIDITY
                event.address = pool_address
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {ONEINCH_LIQUIDITY_LABEL} pool'  # noqa: E501
                receive_events.append(event)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == pool_address and
                event.asset == self.node_inquirer.native_token
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REFUND
                event.counterparty = CPT_ONEINCH_LIQUIDITY
                event.notes = f'Refund of {event.amount} {self.node_inquirer.native_token.symbol} from {ONEINCH_LIQUIDITY_LABEL} pool due to price change'  # noqa: E501
                receive_events.append(event)

        if len(deposit_events) == 0 or len(receive_events) == 0:
            return False

        maybe_reshuffle_events(
            ordered_events=deposit_events + receive_events,
            events_list=decoded_events,
        )
        return True

    def _process_withdrawal(
            self,
            pool_address: ChecksumEvmAddress,
            decoded_events: list[EvmEvent],
    ) -> bool:
        """Turn the transfers of a pool withdrawal into return wrapped and withdrawal events.
        Returns whether the events were found.
        """
        return_events, withdrawal_events = [], []
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS and
                event.asset.identifier.endswith(pool_address)  # the pool's own token
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_ONEINCH_LIQUIDITY
                event.address = pool_address
                event.notes = f'Return {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} to {ONEINCH_LIQUIDITY_LABEL} pool'  # noqa: E501
                return_events.append(event)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == pool_address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_ONEINCH_LIQUIDITY
                event.notes = f'Withdraw {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {ONEINCH_LIQUIDITY_LABEL} pool {pool_address}'  # noqa: E501
                withdrawal_events.append(event)

        if len(return_events) == 0 or len(withdrawal_events) == 0:
            return False

        maybe_reshuffle_events(
            ordered_events=return_events + withdrawal_events,
            events_list=decoded_events,
        )
        return True

    def _process_pool_events(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        for tx_log in self._find_pool_logs(all_logs):
            processed = (
                self._process_deposit(pool_address=tx_log.address, decoded_events=decoded_events)
                if tx_log.topics[0] == DEPOSITED else
                self._process_withdrawal(pool_address=tx_log.address, decoded_events=decoded_events)  # noqa: E501
            )
            if processed is False:
                log.error(
                    'Failed to find the transfers of a 1inch liquidity pool interaction',
                    tx_hash=transaction.tx_hash.hex(),
                    pool_address=tx_log.address,
                )

        return decoded_events

    # -- DecoderInterface methods

    def enricher_rules(self) -> list[Callable]:
        return [self._maybe_enrich_pool_token_transfer]

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_ONEINCH_LIQUIDITY: [(0, self._process_pool_events)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ONEINCH_LIQUIDITY_CPT_DETAILS,)
