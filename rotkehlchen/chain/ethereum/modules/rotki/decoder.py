import logging
from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import (
    DecoderContext,
    EvmDecoderInterface,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_EVM_DECODING_OUTPUT
from rotkehlchen.constants.resolver import tokenid_belongs_to_collection
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

from .constants import (
    CPT_ROTKI,
    ROTKI_NFT_MINTED_TOPIC,
    ROTKI_SPONSORSHIP_COLLECTION_IDENTIFIER,
    ROTKI_SPONSORSHIP_CONTRACT_ADDRESS,
    ROTKI_SPONSORSHIP_TIER_MAPPING,
    ROTKI_SPONSORSHIP_TREASURY_ADDRESS,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkiDecoder(EvmDecoderInterface):

    @staticmethod
    def _decode_nft_events(context: DecoderContext) -> EvmDecodingOutput:
        """Decode Rotki sponsorship NFT minting events."""
        if context.tx_log.topics[0] != ROTKI_NFT_MINTED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        if (tier := ROTKI_SPONSORSHIP_TIER_MAPPING.get(raw_tier := int.from_bytes(context.tx_log.topics[3]))) is None:  # noqa: E501
            log.error(f'Unsupported rotki sponsorship tier {raw_tier} in {context.transaction}')
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address in (ROTKI_SPONSORSHIP_TREASURY_ADDRESS, ROTKI_SPONSORSHIP_CONTRACT_ADDRESS)  # noqa: E501
            ):
                event.counterparty = CPT_ROTKI
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Spend {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} to purchase rotki {tier} Sponsorship NFT'  # noqa: E501

            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == ZERO_ADDRESS and
                    tokenid_belongs_to_collection(event.asset.identifier, ROTKI_SPONSORSHIP_COLLECTION_IDENTIFIER)  # noqa: E501
            ):
                event.counterparty = CPT_ROTKI
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive rotki {tier} Sponsorship NFT'

        return EvmDecodingOutput(process_swaps=True)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {ROTKI_SPONSORSHIP_CONTRACT_ADDRESS: (self._decode_nft_events,)}

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_ROTKI,
            label='rotki',
            image='rotki.svg',
        ),)
