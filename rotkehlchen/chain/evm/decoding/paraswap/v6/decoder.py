import logging
from abc import ABC
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import token_raw_value_decimals
from rotkehlchen.chain.evm.decoding.paraswap.constants import CPT_PARASWAP
from rotkehlchen.chain.evm.decoding.paraswap.decoder import ParaswapCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    DecoderContext,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import TokenKind
from rotkehlchen.utils.misc import address_to_bytes32

from .constants import (
    PARASWAP_AUGUSTUS_V6_ROUTER,
    PARASWAP_METHODS,
    PARASWAP_V6_FEE_CLAIMER,
    SWAP_EXACT_AMOUNT_IN,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Paraswapv6CommonDecoder(ParaswapCommonDecoder, ABC):

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=PARASWAP_AUGUSTUS_V6_ROUTER,
            fee_receiver_address=PARASWAP_V6_FEE_CLAIMER,
        )

    def _handle_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        """Decode Paraswap v6 swaps in post decoding
        since they don't have any relevant log event.
        """
        transfer_event = next(  # detect paraswap labeled events by the enricher logic
            (
                event for event in decoded_events
                if event.counterparty == CPT_PARASWAP and event.event_type == HistoryEventType.SPEND  # noqa: E501
            ),
            None,
        )

        if len(all_logs) == 0:  # needed for the fee event sequence index below
            return decoded_events

        candidate_events = None
        if (
            transfer_event is None and
            transaction.input_data[:4] not in PARASWAP_METHODS and
            (candidate_events := self._find_executor_swap(transaction, decoded_events)) is None
        ):
            return decoded_events

        self._decode_swap(
            context=DecoderContext(
                tx_log=all_logs[-1],  # only referenced to set sequence index for new fee events
                transaction=transaction,
                action_items=[],
                decoded_events=decoded_events,
                all_logs=all_logs,
            ),
            sender=(
                string_to_evm_address(transfer_event.location_label)
                if transfer_event is not None and transfer_event.location_label is not None
                else transaction.from_address
            ),
            candidate_events=candidate_events,
        )

        return decoded_events

    def _find_executor_swap(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
    ) -> tuple[EvmEvent, EvmEvent] | None:
        """Match an exact-input swap wrapped in a delegated account's call to itself."""
        if transaction.to_address != transaction.from_address:
            return None

        spends, payouts = [], []
        for event in decoded_events:
            if (
                event.location_label != transaction.from_address or
                event.event_subtype != HistoryEventSubType.NONE or
                event.counterparty is not None or
                not isinstance(event.asset, EvmToken) or
                event.asset.token_kind != TokenKind.ERC20
            ):
                continue

            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.address == self.router_address
            ):
                payouts.append((event, event.asset))
            elif (
                event.event_type == HistoryEventType.SPEND and
                (executor := event.address) is not None
            ):
                spends.append((event, event.asset, executor))

        if len(payouts) != 1:
            return None

        payout, output_token = payouts[0]
        # The first ABI words of swapExactAmountIn are the executor, input token,
        # output token and raw input amount. Match them to the observed transfers
        # inside the wallet call without relying on the wallet's execution ABI.
        matching_spends = [
            spend for spend, input_token, executor in spends
            if spend.sequence_index < payout.sequence_index and input_token != output_token and
            b''.join((
                SWAP_EXACT_AMOUNT_IN,
                address_to_bytes32(executor),
                address_to_bytes32(input_token.evm_address),
                address_to_bytes32(output_token.evm_address),
                token_raw_value_decimals(spend.amount, input_token.decimals).to_bytes(32),
            )) in transaction.input_data
        ]
        return (matching_spends[0], payout) if len(matching_spends) == 1 else None

    def _maybe_enrich_swap_transfer(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """Label ParaSwap V6 swap transfers with the ParaSwap counterparty.

        ParaSwap V6 does not emit a dedicated swap event; swaps surface only as
        two ERC-20 transfers to/from the Augustus V6 router. Our usual decoding
        (based on calldata plus post-decode heuristics) can fail when the caller
        is a smart contract (such as Gnosis Safe), since they wrap the underlying call.

        If the transfer's `address` is the ParaSwap router, this enricher:
            - sets `context.event.counterparty` to `CPT_PARASWAP`, and
            - returns `TransferEnrichmentOutput(matched_counterparty=CPT_PARASWAP)`.

        This makes non-EoA ParaSwap swaps discoverable by post decoding logic
        that depends on counterparty/location labels.
        """
        if (
            context.event.address != PARASWAP_AUGUSTUS_V6_ROUTER or
            context.event.event_type != HistoryEventType.SPEND
        ):
            return FAILED_ENRICHMENT_OUTPUT

        context.event.counterparty = CPT_PARASWAP
        return TransferEnrichmentOutput(matched_counterparty=CPT_PARASWAP)

    # -- DecoderInterface methods

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.router_address: CPT_PARASWAP}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_PARASWAP: [(0, self._handle_post_decoding)]}

    def enricher_rules(self) -> list[Callable]:
        return [self._maybe_enrich_swap_transfer]
