from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.aave.common import asset_to_atoken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V1
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

DEPOSIT = b'\xc1,W\xb1\xc7:,:.\xa4a>\x94v\xab\xb3\xd8\xd1F\x85z\xabs)\xe2BC\xfbYq\x0c\x82'
REDEEM_UNDERLYING = b'\x9cN\xd5\x99\xcd\x85U\xb9\xc1\xe8\xcdvC$\r}q\xebv\xb7\x92\x94\x8cI\xfc\xb4\xd4\x11\xf7\xb6\xb3\xc6'  # noqa: E501
LIQUIDATION_CALL = b'V\x86GW\xfd[\x1f\xc9\xf3\x8f_:\x98\x1c\xd8\xaeQ,\xe4\x1b\x90,\xf7?\xc5\x06\xee6\x9ck\xc27'  # noqa: E501


class Aavev1Decoder(EvmDecoderInterface):

    def _decode_pool_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT:
            return self._decode_deposit_event(context=context)
        if context.tx_log.topics[0] == REDEEM_UNDERLYING:
            return self._decode_redeem_underlying_event(context=context)
        if context.tx_log.topics[0] == LIQUIDATION_CALL:
            return self._decode_liquidation(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_deposit_event(self, context: DecoderContext) -> EvmDecodingOutput:
        reserve_address = bytes_to_address(context.tx_log.topics[1])
        reserve_asset = self.base.get_or_create_evm_asset(reserve_address)
        user_address = bytes_to_address(context.tx_log.topics[2])
        raw_amount = int.from_bytes(context.tx_log.data[0:32])
        amount = asset_normalized_value(raw_amount, reserve_asset)
        atoken = asset_to_atoken(asset=reserve_asset, version=1)
        if atoken is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        deposit_event = receive_event = None
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.location_label == user_address and amount == event.amount and reserve_asset == event.asset:  # noqa: E501
                # find the deposit transfer (can also be an ETH internal transfer)
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Deposit {amount} {reserve_asset.symbol} to aave-v1 from {event.location_label}'  # noqa: E501
                deposit_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.amount and atoken == event.asset:  # noqa: E501
                # find the receive aToken transfer
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Receive {amount} {atoken.symbol} from aave-v1 for {event.location_label}'  # noqa: E501
                receive_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and event.address == ZERO_ADDRESS and event.asset == atoken:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Gain {event.amount} {atoken.symbol} from aave-v1 as interest'

        maybe_reshuffle_events(
            ordered_events=[deposit_event, receive_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_redeem_underlying_event(self, context: DecoderContext) -> EvmDecodingOutput:
        reserve_address = bytes_to_address(context.tx_log.topics[1])
        reserve_asset = self.base.get_or_create_evm_asset(reserve_address)
        user_address = bytes_to_address(context.tx_log.topics[2])
        raw_amount = int.from_bytes(context.tx_log.data[0:32])
        amount = asset_normalized_value(raw_amount, reserve_asset)
        atoken = asset_to_atoken(asset=reserve_asset, version=1)
        if atoken is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        receive_event = return_event = interest_event = None
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.amount and reserve_asset == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Withdraw {amount} {reserve_asset.symbol} from aave-v1'
                receive_event = event
            elif event.event_type == HistoryEventType.SPEND and event.location_label == user_address and amount == event.amount and atoken == event.asset:  # noqa: E501
                # find the redeem aToken transfer
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Return {amount} {atoken.symbol} to aave-v1'
                return_event = event
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and event.address == ZERO_ADDRESS and event.asset == atoken:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Gain {event.amount} {atoken.symbol} from aave-v1 as interest'
                interest_event = event

        maybe_reshuffle_events(
            ordered_events=[return_event, receive_event, interest_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_liquidation(self, context: DecoderContext) -> EvmDecodingOutput:
        """
        Decode AAVE v1 liquidations. When a liquidation happens the user returns the debt token.
        """
        if self.base.is_tracked(bytes_to_address(context.tx_log.topics[3])) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            asset = event.asset.resolve_to_evm_token()
            if event.event_type == HistoryEventType.SPEND and asset_normalized_value(
                amount=int.from_bytes(context.tx_log.data[32:64]),  # debt amount
                asset=asset,
            ) == event.amount:
                # we are transferring the debt token
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.notes = f'Payback {event.amount} {asset.symbol} for an aave-v1 position'
                event.counterparty = CPT_AAVE_V1
                event.address = context.tx_log.address
                event.extra_data = {'is_liquidation': True}  # adding this field to the decoded event to differentiate paybacks happening in liquidations.  # noqa: E501
            elif event.event_type == HistoryEventType.RECEIVE:
                event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                event.counterparty = CPT_AAVE_V1
                event.notes = f'Interest payment of {event.amount} {asset.symbol} for aave-v1 position'  # noqa: E501
                event.address = context.tx_log.address

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            string_to_evm_address('0x398eC7346DcD622eDc5ae82352F02bE94C62d119'): (self._decode_pool_event,),  # AAVE_V1_LENDING_POOL  # noqa: E501
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_AAVE_V1,
            image='aave.svg',
        ),)
