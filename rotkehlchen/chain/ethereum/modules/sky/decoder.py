import logging
from typing import Any

from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_DAI, A_MKR
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import (
    CPT_SKY,
    DAI_TO_USDS,
    DAI_TO_USDS_CONTRACT,
    DEPOSIT_USDS,
    MKR_TO_SKY,
    MKR_TO_SKY_CONTRACT,
    SKY_ASSET,
    SUSDS_ASSET,
    SUSDS_CONTRACT,
    USDS_ASSET,
    WITHDRAW_USDS,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SkyDecoder(DecoderInterface):

    def _decode_migrate_dai(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != DAI_TO_USDS:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = hex_or_bytes_to_int(context.tx_log.data[0:32])
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if event.balance.amount != amount:
                continue

            if (
                event.event_type == HistoryEventType.SPEND and
                event.asset == A_DAI
            ):
                event.counterparty = CPT_SKY
                event.event_type = HistoryEventType.MIGRATE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Migrate {amount} DAI to USDS'
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.asset == USDS_ASSET
            ):
                event.counterparty = CPT_SKY
                event.event_type = HistoryEventType.MIGRATE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {amount} USDS from DAI->USDS migration'

        return DEFAULT_DECODING_OUTPUT

    def _decode_migrate_mkr(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != MKR_TO_SKY:
            return DEFAULT_DECODING_OUTPUT

        mkr_amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        sky_amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        user = hex_or_bytes_to_address(context.tx_log.topics[2])
        mkr_event, sky_event = None, None
        for event in context.decoded_events:
            if (
                event.location_label == user and
                event.balance.amount == mkr_amount and
                event.asset == A_MKR
            ):
                event.counterparty = CPT_SKY
                event.event_type = HistoryEventType.MIGRATE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Migrate {mkr_amount} MKR to SKY'
                mkr_event = event
            elif (
                event.location_label == user and
                event.balance.amount == sky_amount and
                event.asset == SKY_ASSET and
                event.event_type == HistoryEventType.RECEIVE
            ):
                event.counterparty = CPT_SKY
                event.event_type = HistoryEventType.MIGRATE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {sky_amount} SKY from MKR->SKY migration'
                sky_event = event

        if None in (mkr_event, sky_event):
            log.error(f'Failed to decode mkr migration at {context.transaction}')
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events([mkr_event, sky_event], context.decoded_events)
        return DEFAULT_DECODING_OUTPUT

    def _decode_susds_events(self, context: DecoderContext) -> DecodingOutput:
        if not (
            (is_deposit := context.tx_log.topics[0] == DEPOSIT_USDS) or
            context.tx_log.topics[0] == WITHDRAW_USDS
        ):
            return DEFAULT_DECODING_OUTPUT

        received_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        if (assets_amount := token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )) == ZERO:
            return DEFAULT_DECODING_OUTPUT

        shares_amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )

        action_items = []
        if is_deposit:
            action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=SUSDS_ASSET,
                amount=shares_amount,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
                to_counterparty=CPT_SKY,
                to_notes=f'Withdraw {shares_amount} sUSDS from sUSDS contract',
            ))

        in_event, out_event = None, None
        for event in context.decoded_events:
            if not (
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == received_address
            ):
                continue

            if (is_incoming_event := event.event_type == HistoryEventType.RECEIVE):
                event_type = HistoryEventType.WITHDRAWAL
                event_subtype = HistoryEventSubType.REMOVE_ASSET
            else:
                event_type = HistoryEventType.DEPOSIT
                event_subtype = HistoryEventSubType.DEPOSIT_ASSET

            if (
                event.balance.amount == assets_amount and
                event.asset == USDS_ASSET
            ):
                event.counterparty = CPT_SKY
                event.event_type = event_type
                event.event_subtype = event_subtype
                if is_incoming_event:
                    in_event = event
                else:
                    out_event = event

                if is_deposit:
                    verb, preposition = ('Withdraw', 'from') if is_incoming_event else ('Deposit', 'to')  # noqa: E501
                    event.notes = f'{verb} {event.balance.amount} USDS {preposition} sUSDS contract'  # noqa: E501
                else:
                    verb, preposition = ('Withdraw', 'from') if is_incoming_event else ('Return', 'to')  # noqa: E501
                    event.notes = f'{verb} {event.balance.amount} USDS {preposition} sUSDS contract'  # noqa: E501

            elif event.balance.amount == shares_amount and event.asset == SUSDS_ASSET:
                event.counterparty = CPT_SKY
                event.event_type = event_type
                event.event_subtype = event_subtype
                if is_incoming_event:
                    in_event = event
                else:
                    out_event = event

                verb, preposition = ('Withdraw', 'from') if is_incoming_event and not is_deposit else ('Return', 'to')  # noqa: E501
                event.notes = f'{verb} {event.balance.amount} sUSDS {preposition} sUSDS contract'

        if not is_deposit and None in (in_event, out_event):
            log.error(f'Failed to decode sUSDS event at {context.transaction}')
            return DecodingOutput(action_items=action_items)

        maybe_reshuffle_events([out_event, in_event], context.decoded_events)
        return DecodingOutput(action_items=action_items)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            DAI_TO_USDS_CONTRACT: (self._decode_migrate_dai,),
            SUSDS_CONTRACT: (self._decode_susds_events,),
            MKR_TO_SKY_CONTRACT: (self._decode_migrate_mkr,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_SKY, label='Sky', image='sky_money.svg'),)
