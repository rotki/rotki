import logging
from typing import Callable

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import DecoderEventMappingType
from rotkehlchen.utils.misc import (
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
    hex_or_bytes_to_str,
)

from .constants import CPT_SAFE_MULTISIG

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SafemultisigDecoder(DecoderInterface):
    def _decode_added_owner(self, context: DecoderContext) -> DecodingOutput:
        address = hex_or_bytes_to_address(context.tx_log.data[:32])
        if not self.base.any_tracked([address, context.transaction.from_address, context.tx_log.address]):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

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
        if not self.base.any_tracked([address, context.transaction.from_address, context.tx_log.address]):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

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
        if not self.base.any_tracked([context.transaction.from_address, context.tx_log.address]):
            return DEFAULT_DECODING_OUTPUT

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

    def _decode_execution_success(self, context: DecoderContext) -> DecodingOutput:
        """Decodes the execution success message. We only add an event only if other
        safe specific events are not included for this safe. That's in order to not
        have too many events spamming if owners are added, removed etc."""
        for event in context.decoded_events:
            if event.counterparty == CPT_SAFE_MULTISIG and event.address == context.tx_log.address:
                return DEFAULT_DECODING_OUTPUT  # only add if no other safe-specific events exist

        if not self.base.any_tracked([context.transaction.from_address, context.tx_log.address]):
            return DEFAULT_DECODING_OUTPUT

        safe_tx_hash = hex_or_bytes_to_str(context.tx_log.data[:32])
        event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Successfully executed safe transaction 0x{safe_tx_hash} for multisig {context.tx_log.address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=context.tx_log.address,
        )
        return DecodingOutput(event=event)

    def decode_safe_creation(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.any_tracked([context.transaction.from_address, context.tx_log.address]):
            return DEFAULT_DECODING_OUTPUT

        num_owners = (len(context.tx_log.data) // 32) - 5  # data has 5 elements that are not the addresses  # noqa: E501
        owners = []
        # chunk the data and iterate in reverse order. First elements are the owners and then
        # comes the threshold
        threshold = 0
        for index, entry in enumerate(reversed([context.tx_log.data[i:i + 32] for i in range(0, len(context.tx_log.data), 32)])):  # noqa: E501
            if index < num_owners:
                owners.append(hex_or_bytes_to_address(entry))
            elif index == num_owners:
                threshold = hex_or_bytes_to_int(entry)
            else:
                break

        event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Create a new safe with a threshold of {threshold} and owners {",".join(owners)}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=context.tx_log.address,
        )
        return DecodingOutput(event=event)

    def _decode_execution_failure(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.any_tracked([context.transaction.from_address, context.tx_log.address]):
            return DEFAULT_DECODING_OUTPUT

        safe_tx_hash = hex_or_bytes_to_str(context.tx_log.data[:32])
        event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Failed to execute safe transaction 0x{safe_tx_hash} for multisig {context.tx_log.address}',  # noqa: E501
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
                b"D.q_bcF\xe8\xc5C\x81\x00-\xa6\x14\xf6+\xee\x8d'8e5\xb2R\x1e\xc8T\x08\x98Un": self._decode_execution_success,  # noqa: E501
                b'#B\x8b\x18\xac\xfb>\xa6K\x08\xdc\x0c\x1d)n\xa9\xc0\x97\x02\xc0\x90\x83\xcaRr\xe6M\x11[h}#': self._decode_execution_failure,  # noqa: E501
            },
            b'\x16\x88\xf0\xb9': {  # createProxyWithNonce
                b'\x14\x1d\xf8h\xa63\x1a\xf5(\xe3\x8c\x83\xb7\xaa\x03\xed\xc1\x9b\xe6n7\xaeg\xf9([\xf4\xf8\xe3\xc6\xa1\xa8': self.decode_safe_creation,  # noqa: E501
            },
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(
            identifier=CPT_SAFE_MULTISIG,
            label='Safe Multisig',
            image='safemultisig.svg',
        )]
