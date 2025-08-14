import logging
from typing import Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_GLM
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_GOLEM, GNT_MIGRATION_ADDRESS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MIGRATED = b'\x92\x8f\xd5S\x13$\xee\x87\xd7l\xc50}\xc3u\x80\x17M\xa7k\x85\xcdTm\xa61\xb2g\x0b\xc2f\xb5'  # noqa: E501


class GolemDecoder(DecoderInterface):

    def _decode_migration(self, context: DecoderContext) -> DecodingOutput:
        """Decode GNT -> GLM migration"""
        if context.tx_log.topics[0] != MIGRATED:
            return DEFAULT_DECODING_OUTPUT

        from_address = bytes_to_address(context.tx_log.data[:32])

        if not self.base.is_tracked(from_address):
            return DEFAULT_DECODING_OUTPUT

        amount_raw = int.from_bytes(context.tx_log.data[64:96])
        amount = token_normalized_value_decimals(amount_raw, 18)

        # Create the GNT out event, since no transfer event is emitted
        out_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.MIGRATE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d'),
            amount=amount,
            location_label=from_address,
            notes=f'Migrate {amount} GNT to GLM',
            counterparty=CPT_GOLEM,
            address=GNT_MIGRATION_ADDRESS,
        )
        # now find the GLM in event, edit it and push it after the out event
        in_event = None
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_GLM and event.amount == amount and event.location_label == from_address:  # noqa: E501
                event.event_type = HistoryEventType.MIGRATE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {amount} GLM from GNT->GLM migration'
                event.counterparty = CPT_GOLEM
                event.address = GNT_MIGRATION_ADDRESS
                in_event = event
                break
        else:
            log.error(f'During Golem GNT->GLM migration did not find the receiving event in tx: {context.transaction.tx_hash.hex()}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DecodingOutput(events=[out_event], refresh_balances=False)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {GNT_MIGRATION_ADDRESS: (self._decode_migration,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_GOLEM, label='Golem', image='golem.svg'),)
