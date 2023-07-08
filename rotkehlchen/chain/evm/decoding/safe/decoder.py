import logging
from typing import Callable

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import DecoderEventMappingType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_SAFE_MULTISIG

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SafemultisigDecoder(DecoderInterface):
    def _decode_added_owner(self, context: DecoderContext) -> DecodingOutput:
        address = hex_or_bytes_to_address(context.tx_log.data[:32])
        event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Add owner {address} to multisig {context.tx_log.address}',
            counterparty=CPT_SAFE_MULTISIG,
            address=context.tx_log.address,
        )
        return DecodingOutput(event=event)

    def _decode_removed_owner(self, context: DecoderContext) -> DecodingOutput:
        address = hex_or_bytes_to_address(context.tx_log.data[:32])
        event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Remove owner {address} from multisig {context.tx_log.address}',
            counterparty=CPT_SAFE_MULTISIG,
            address=context.tx_log.address,
        )
        return DecodingOutput(event=event)

    def _decode_changed_threshold(self, context: DecoderContext) -> DecodingOutput:
        threshold = hex_or_bytes_to_int(context.tx_log.data[:32])
        event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Change signers threshold to {threshold} for multisig {context.tx_log.address}',
            counterparty=CPT_SAFE_MULTISIG,
            address=context.tx_log.address,
        )
        return DecodingOutput(event=event)

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {
            CPT_SAFE_MULTISIG: {
                HistoryEventType.INFORMATIONAL: {
                    HistoryEventSubType.NONE: EventCategory.INFORMATIONAL,
                },
            },
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {
            b'jv\x12\x02': {
                b'\x94e\xfa\x0c\x96,\xc7iX\xe67:\x993&@\x0c\x1c\x94\xf8\xbe/\xe3\xa9R\xad\xfa\x7f`\xb2\xea&': self._decode_added_owner,  # noqa: E501
                b'\xf8\xd4\x9f\xc5)\x81.\x9a|\\P\xe6\x9c \xf0\xdc\xcc\r\xb8\xfa\x95\xc9\x8b\xc5\x8c\xc9\xa4\xf1\xc1)\x9e\xaf': self._decode_removed_owner,  # noqa: E501
                b'a\x0f\x7f\xf2\xb3\x04\xae\x89\x03\xc3\xdet\xc6\x0cj\xb1\xf7\xd6"k?R\xc5\x16\x19\x05\xbbZ\xd4\x03\x9c\x93': self._decode_changed_threshold,  # noqa: E501
            },
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(
            identifier=CPT_SAFE_MULTISIG,
            label='Safe Multisig',
            image='safemultisig.svg',
        )]
