import logging
from abc import ABC
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.paraswap.constants import CPT_PARASWAP
from rotkehlchen.chain.evm.decoding.paraswap.decoder import ParaswapCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    DecoderContext,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

from .constants import PARASWAP_AUGUSTUS_V6_ROUTER, PARASWAP_METHODS, PARASWAP_V6_FEE_CLAIMER

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Paraswapv6CommonDecoder(ParaswapCommonDecoder, ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
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
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
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

        if ((
                transfer_event is None and
                transaction.input_data[:4] not in PARASWAP_METHODS
        ) or len(all_logs) == 0):  # length check is to protect due to all_logs[-1] below
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
        )

        return decoded_events

    def _maybe_enrich_swap_transfer(
            self,
            context: 'EnricherContext',
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
