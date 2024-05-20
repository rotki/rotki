from typing import Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_AAVE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import REDEEM_AAVE, STAKED_AAVE, STK_AAVE_ADDR, STKAAVE_IDENTIFIER


class AaveDecoder(DecoderInterface):
    """Aave decoder for staking and unstaking events"""
    def _decode_staking_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode aave staking unstaking events"""
        if context.tx_log.topics[0] == STAKED_AAVE:
            method = self._decode_stake
        elif context.tx_log.topics[0] == REDEEM_AAVE:
            method = self._decode_unstake
        else:
            return DEFAULT_DECODING_OUTPUT

        from_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        to_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        return method(from_address=from_address, to_address=to_address, amount=amount, decoded_events=context.decoded_events)  # noqa: E501

    def _decode_stake(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            amount: FVal,
            decoded_events: list[EvmEvent],
    ) -> DecodingOutput:
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_AAVE and
                event.location_label == to_address and
                event.balance.amount == amount
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Stake {amount} AAVE'
                if from_address != to_address:
                    event.notes += f' for {to_address}'
                event.product = EvmProduct.STAKING
                event.counterparty = CPT_AAVE
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == STKAAVE_IDENTIFIER and
                event.location_label == to_address and
                event.balance.amount == amount
            ):
                event.counterparty = CPT_AAVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {event.balance.amount} stkAAVE from staking in Aave'

        return DEFAULT_DECODING_OUTPUT

    def _decode_unstake(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            amount: FVal,
            decoded_events: list[EvmEvent],
    ) -> DecodingOutput:
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == STKAAVE_IDENTIFIER and
                event.location_label == to_address and
                event.balance.amount == amount
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Unstake {amount} stkAAVE'
                if from_address != to_address:
                    event.notes += f' for {to_address}'
                event.product = EvmProduct.STAKING
                event.counterparty = CPT_AAVE
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_AAVE and
                event.location_label == to_address and
                event.balance.amount == amount
            ):
                event.counterparty = CPT_AAVE
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Receive {event.balance.amount} AAVE after unstaking from Aave'

        return DEFAULT_DECODING_OUTPUT

    # DecoderInterface method
    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {STK_AAVE_ADDR: (self._decode_staking_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_AAVE,
            label=CPT_AAVE.capitalize(),
            image='aave.svg',
        ),)
