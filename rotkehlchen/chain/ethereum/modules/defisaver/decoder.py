import logging
from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_DEFISAVER, DEACTIVATE_SUB, SUB_STORAGE, SUBSCRIBE

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DefisaverDecoder(EvmDecoderInterface):

    def _decode_subscribe(self, context: DecoderContext) -> DecodingOutput:
        sub_id = int.from_bytes(context.tx_log.topics[1])
        proxy = bytes_to_address(context.tx_log.topics[2])
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Subscribe to defisaver automation with subscription id {sub_id} for proxy {proxy}',  # noqa: E501
            address=context.tx_log.address,
            counterparty=CPT_DEFISAVER,
        )
        return DecodingOutput(events=[event])

    def _decode_deactivate_sub(self, context: DecoderContext) -> DecodingOutput:
        sub_id = int.from_bytes(context.tx_log.topics[1])
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Deactivate defisaver automation subscription with id {sub_id}',
            address=context.tx_log.address,
            counterparty=CPT_DEFISAVER,
        )
        return DecodingOutput(events=[event])

    def _decode_substorage_action(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == DEACTIVATE_SUB:
            return self._decode_deactivate_sub(context)
        if context.tx_log.topics[0] == SUBSCRIBE:
            return self._decode_subscribe(context)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {SUB_STORAGE: (self._decode_substorage_action,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_DEFISAVER,
            label='Defisaver',
            image='defisaver.jpeg',
        ),)
