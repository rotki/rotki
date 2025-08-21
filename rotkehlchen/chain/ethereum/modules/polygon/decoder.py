import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.polygon.constants import CPT_POLYGON, CPT_POLYGON_DETAILS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_ETH_MATIC, A_POL
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import POLYGON_MIGRATION_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MIGRATED = b'\x8b\x80\xbd\x19\xae\xa7\xb75\xbcmu\xdb\x8dj\xdb\xe1\x8b(\xc3\rb\xb3URE\xebg\xb24\x0c\xae\xdc'  # noqa: E501


class PolygonDecoder(DecoderInterface):
    """General polygon related decoder for ethereum mainnet. For now matic->pol migration"""

    def _decode_migration(self, context: DecoderContext) -> DecodingOutput:
        """Decode a MATIC -> POL migration"""
        if context.tx_log.topics[0] != MIGRATED:
            return DEFAULT_DECODING_OUTPUT

        account = bytes_to_address(context.tx_log.topics[1])
        if not self.base.is_tracked(account):
            return DEFAULT_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[:32])
        amount = token_normalized_value_decimals(raw_amount, 18)

        action_items = [ActionItem(
            action='transform',
            from_event_type=from_type,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=asset,
            amount=amount,
            to_event_type=HistoryEventType.MIGRATE,
            to_event_subtype=to_subtype,
            to_notes=notes,
            to_counterparty=CPT_POLYGON,
            to_address=POLYGON_MIGRATION_ADDRESS,
        ) for from_type, asset, to_subtype, notes in (
            (HistoryEventType.SPEND, A_ETH_MATIC, HistoryEventSubType.SPEND, f'Migrate {amount} MATIC to POL'),  # noqa: E501
            (HistoryEventType.RECEIVE, A_POL, HistoryEventSubType.RECEIVE, f'Receive {amount} POL from MATIC->POL migration'),  # noqa: E501
        )]
        return DecodingOutput(action_items=action_items, matched_counterparty=CPT_POLYGON)

    def _handle_post_decoding(
            self,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Handle post decoding for polygon migration. Simply enforces event order"""
        out_event, in_event = None, None
        for event in decoded_events:
            if event.counterparty == CPT_POLYGON and event.event_type == HistoryEventType.MIGRATE:
                if event.event_subtype == HistoryEventSubType.SPEND:
                    out_event = event
                if event.event_subtype == HistoryEventSubType.RECEIVE:
                    in_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )
        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {POLYGON_MIGRATION_ADDRESS: (self._decode_migration,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CPT_POLYGON_DETAILS,)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_POLYGON: [(0, self._handle_post_decoding)]}
