from typing import Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.aave.common import asset_to_atoken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, ethaddress_to_asset
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import AAVE_LABEL, CPT_AAVE_V1

DEPOSIT = b'\xc1,W\xb1\xc7:,:.\xa4a>\x94v\xab\xb3\xd8\xd1F\x85z\xabs)\xe2BC\xfbYq\x0c\x82'
REDEEM_UNDERLYING = b'\x9cN\xd5\x99\xcd\x85U\xb9\xc1\xe8\xcdvC$\r}q\xebv\xb7\x92\x94\x8cI\xfc\xb4\xd4\x11\xf7\xb6\xb3\xc6'  # noqa: E501


class Aavev1Decoder(DecoderInterface):

    def _decode_pool_event(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT:
            return self._decode_deposit_event(context=context)
        if context.tx_log.topics[0] == REDEEM_UNDERLYING:
            return self._decode_redeem_underlying_event(context=context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_deposit_event(self, context: DecoderContext) -> DecodingOutput:
        reserve_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        reserve_asset = ethaddress_to_asset(reserve_address)
        if reserve_asset is None:
            return DEFAULT_DECODING_OUTPUT
        user_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        raw_amount = hex_or_bytes_to_int(context.tx_log.data[0:32])
        amount = asset_normalized_value(raw_amount, reserve_asset)
        atoken = asset_to_atoken(asset=reserve_asset, version=1)
        if atoken is None:
            return DEFAULT_DECODING_OUTPUT

        deposit_event = receive_event = None
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.location_label == user_address and amount == event.balance.amount and reserve_asset == event.asset:  # noqa: E501
                # find the deposit transfer (can also be an ETH internal transfer)
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Deposit {amount} {reserve_asset.symbol} to aave-v1 from {event.location_label}'  # noqa: E501
                deposit_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and atoken == event.asset:  # noqa: E501
                # find the receive aToken transfer
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Receive {amount} {atoken.symbol} from aave-v1 for {event.location_label}'  # noqa: E501
                receive_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and event.address == ZERO_ADDRESS and event.asset == atoken:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Gain {event.balance.amount} {atoken.symbol} from aave-v1 as interest'  # noqa: E501

        maybe_reshuffle_events(out_event=deposit_event, in_event=receive_event)
        return DEFAULT_DECODING_OUTPUT

    def _decode_redeem_underlying_event(self, context: DecoderContext) -> DecodingOutput:
        reserve_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        reserve_asset = ethaddress_to_asset(reserve_address)
        if reserve_asset is None:
            return DEFAULT_DECODING_OUTPUT
        user_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        raw_amount = hex_or_bytes_to_int(context.tx_log.data[0:32])
        amount = asset_normalized_value(raw_amount, reserve_asset)
        atoken = asset_to_atoken(asset=reserve_asset, version=1)
        if atoken is None:
            return DEFAULT_DECODING_OUTPUT

        receive_event = return_event = None
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and reserve_asset == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Withdraw {amount} {reserve_asset.symbol} from aave-v1'
                receive_event = event
            elif event.event_type == HistoryEventType.SPEND and event.location_label == user_address and amount == event.balance.amount and atoken == event.asset:  # noqa: E501
                # find the redeem aToken transfer
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Return {amount} {atoken.symbol} to aave-v1'
                return_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and event.address == ZERO_ADDRESS and event.asset == atoken:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Gain {event.balance.amount} {atoken.symbol} from aave-v1 as interest'  # noqa: E501

        maybe_reshuffle_events(out_event=return_event, in_event=receive_event, events_list=context.decoded_events)  # noqa: E501
        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_AAVE_V1: {
            HistoryEventType.RECEIVE: {
                HistoryEventSubType.REWARD: EventCategory.CLAIM_REWARD,
                HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
            },
            HistoryEventType.DEPOSIT: {
                HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
            },
            HistoryEventType.SPEND: {
                HistoryEventSubType.RETURN_WRAPPED: EventCategory.SEND,
            },
            HistoryEventType.WITHDRAWAL: {
                HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            string_to_evm_address('0x398eC7346DcD622eDc5ae82352F02bE94C62d119'): (self._decode_pool_event,),  # AAVE_V1_LENDING_POOL  # noqa: E501
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(identifier=CPT_AAVE_V1, label=AAVE_LABEL, image='aave.svg')]
