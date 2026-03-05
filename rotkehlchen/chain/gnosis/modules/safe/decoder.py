from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.safe.constants import CPT_SAFE
from rotkehlchen.chain.evm.constants import CLAIMED_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import SAFE_CLAIM_DISTRIBUTOR, SAFE_TOKEN_ID_GNOSIS


class SafeDecoder(EvmDecoderInterface):

    def _decode_safe_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != CLAIMED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.asset.identifier == SAFE_TOKEN_ID_GNOSIS
            ):
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_SAFE
                event.address = context.tx_log.address
                event.notes = f'Claim {event.amount} SAFE from GnosisDAO Safe Token Distribution'
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            SAFE_CLAIM_DISTRIBUTOR: (self._decode_safe_claim,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SAFE,
            label='Safe',
            image='safemultisig.svg',
        ),)
