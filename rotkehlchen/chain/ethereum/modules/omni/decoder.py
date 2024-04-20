import logging
from typing import Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.constants import STAKED
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import (
    CLAIMED,
    CPT_OMNI,
    OMNI_AIDROP_CONTRACT,
    OMNI_STAKING_CONTRACT,
    OMNI_TOKEN_ID,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OmniDecoder(DecoderInterface):

    def _decode_omni_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(claiming_address := hex_or_bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        claimed_amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data),
            token_decimals=18,  # omni has 18 decimals
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == claiming_address and
                event.asset.identifier == OMNI_TOKEN_ID and
                event.balance.amount == claimed_amount
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_OMNI
                event.notes = f'Claim {event.balance.amount} OMNI from the Omni genesis airdrop'
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.address == OMNI_AIDROP_CONTRACT and
                event.asset == A_ETH
            ):
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_OMNI
                event.notes = f'Spend {event.balance.amount} ETH as a fee to claim the Omni genesis airdrop'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_omni_stake(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != STAKED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := hex_or_bytes_to_address(context.tx_log.topics[1])):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        staked_amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data),
            token_decimals=18,  # omni has 18 decimals
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.location_label == user_address and
                event.address == OMNI_STAKING_CONTRACT and
                event.asset.identifier == OMNI_TOKEN_ID and
                event.balance.amount == staked_amount
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_OMNI
                event.notes = f'Stake {event.balance.amount} OMNI'

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            OMNI_AIDROP_CONTRACT: (self._decode_omni_claim,),
            OMNI_STAKING_CONTRACT: (self._decode_omni_stake,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_OMNI, label='Omni', image='diva.svg'),)
