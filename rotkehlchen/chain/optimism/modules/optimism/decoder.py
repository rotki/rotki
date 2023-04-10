from typing import Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType
from rotkehlchen.utils.misc import hex_or_bytes_to_address

OPTIMISM_TOKEN = string_to_evm_address('0x4200000000000000000000000000000000000042')

DELEGATE_CHANGED = b'14\xe8\xa2\xe6\xd9~\x92\x9a~T\x01\x1e\xa5H]}\x19m\xd5\xf0\xbaMN\xf9X\x03\xe8\xe3\xfc%\x7f'  # noqa: E501


class OptimismDecoder(DecoderInterface):

    def _decode_delegate_changed(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != DELEGATE_CHANGED:
            return DEFAULT_DECODING_OUTPUT

        delegator = hex_or_bytes_to_address(context.tx_log.topics[1])
        if not self.base.is_tracked(delegator):
            return DEFAULT_DECODING_OUTPUT

        from_delegate = hex_or_bytes_to_address(context.tx_log.topics[2])
        to_delegate = hex_or_bytes_to_address(context.tx_log.topics[3])
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Change OP Delegate from {from_delegate} to {to_delegate}',
            counterparty=CPT_OPTIMISM,
            address=context.transaction.to_address,
        )
        return DecodingOutput(event=event)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            OPTIMISM_TOKEN: (self._decode_delegate_changed,),
        }

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_OPTIMISM: {
            HistoryEventType.INFORMATIONAL: {
                HistoryEventSubType.GOVERNANCE: EventCategory.GOVERNANCE,
            },
        }}

    def counterparties(self) -> list[CounterpartyDetails]:
        return [OPTIMISM_CPT_DETAILS]
