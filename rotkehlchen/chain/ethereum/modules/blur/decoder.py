import logging
from typing import Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import (
    CLAIMED_TOPIC,
    DEFAULT_TOKEN_DECIMALS,
    DEPOSIT_TOPIC_V2,
    WITHDRAW_TOPIC_V2,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    BLUR_CPT_DETAILS,
    BLUR_DISTRIBUTOR,
    BLUR_IDENTIFIER,
    BLUR_STAKING_CONTRACT,
    CPT_BLUR,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BlurDecoder(DecoderInterface):

    def _decode_staking_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode staking events in the Blur protocol"""
        if context.tx_log.topics[0] == DEPOSIT_TOPIC_V2:
            return self._decode_stake(context)

        if context.tx_log.topics[0] == WITHDRAW_TOPIC_V2:
            return self._decode_unstake(context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_stake(self, context: DecoderContext) -> DecodingOutput:
        """Decode staking event in the Blur protocol"""
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        stake_amount = int.from_bytes(context.tx_log.data[:32])
        stake_amount_norm = token_normalized_value_decimals(
            token_amount=stake_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        # In `depositFromAirdrop()`, the transfer is directly done to the contract
        # and is not decoded but in the case of just `deposit()`, the transfer is decoded
        # so we need to skip the transfer to the contract when the user stakes
        # without claiming otherwise it will duplicate events
        action_item = ActionItem(
            action='skip',
            from_event_type=HistoryEventType.SPEND,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=Asset(BLUR_IDENTIFIER),
            location_label=user_address,
            amount=stake_amount_norm,
        )
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(BLUR_IDENTIFIER),
            amount=stake_amount_norm,
            location_label=user_address,
            notes=f'Stake {stake_amount_norm} BLUR',
            counterparty=CPT_BLUR,
            product=EvmProduct.STAKING,
            address=BLUR_STAKING_CONTRACT,
        )
        return DecodingOutput(action_items=[action_item], events=[event])

    def _decode_unstake(self, context: DecoderContext) -> DecodingOutput:
        """Decode unstaking event in the Blur protocol"""
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == BLUR_IDENTIFIER and
                event.amount == amount and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Unstake {amount} BLUR'
                event.counterparty = CPT_BLUR
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_blur_airdrop_2_claim(self, context: DecoderContext) -> DecodingOutput:
        """Decode airdrop 2 claim event in the Blur protocol"""
        if context.tx_log.topics[0] != CLAIMED_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        if self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])) is False:
            return DEFAULT_DECODING_OUTPUT

        claim_amount = int.from_bytes(context.tx_log.data[:32])
        claim_amount_norm = token_normalized_value_decimals(
            token_amount=claim_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=Asset(BLUR_IDENTIFIER),
            amount=claim_amount_norm,
            location_label=user,
            notes=f'Claim {claim_amount_norm} BLUR from Blur airdrop',
            counterparty=CPT_BLUR,
            address=context.transaction.to_address,
        )
        return DecodingOutput(events=[event])

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (BLUR_CPT_DETAILS,)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            BLUR_STAKING_CONTRACT: (self._decode_staking_events,),
            BLUR_DISTRIBUTOR: (self._decode_blur_airdrop_2_claim,),
        }
