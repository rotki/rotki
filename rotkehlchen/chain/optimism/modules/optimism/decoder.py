from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.constants import DELEGATE_CHANGED, OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_OP
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

OPTIMISM_TOKEN = string_to_evm_address('0x4200000000000000000000000000000000000042')


class OptimismDecoder(EvmDecoderInterface):

    def _decode_delegate_changed(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != DELEGATE_CHANGED:
            return DEFAULT_EVM_DECODING_OUTPUT

        delegator = bytes_to_address(context.tx_log.topics[1])
        if not self.base.is_tracked(delegator):
            return DEFAULT_EVM_DECODING_OUTPUT

        delegator_note = ''
        if delegator != context.transaction.from_address:
            delegator_note = f' for {delegator}'
        from_delegate = bytes_to_address(context.tx_log.topics[2])
        to_delegate = bytes_to_address(context.tx_log.topics[3])
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_OP,
            amount=ZERO,
            location_label=context.transaction.from_address,
            notes=f'Change OP Delegate{delegator_note} from {from_delegate} to {to_delegate}',
            counterparty=CPT_OPTIMISM,
            address=context.transaction.to_address,
        )
        return EvmDecodingOutput(events=[event])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            OPTIMISM_TOKEN: (self._decode_delegate_changed,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (OPTIMISM_CPT_DETAILS,)
