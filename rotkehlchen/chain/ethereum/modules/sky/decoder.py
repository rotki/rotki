import logging
from typing import Any

from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_DAI, A_MKR
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_SKY,
    DAI_TO_USDS,
    DAI_TO_USDS_CONTRACT,
    EXIT,
    MIGRATION_ACTIONS_CONTRACT,
    MKR_TO_SKY,
    MKR_TO_SKY_CONTRACT,
    SKY_ASSET,
    USDS_ASSET,
    USDS_JOIN_ADDRESS,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SkyDecoder(DecoderInterface):

    def _decode_migrate_dai(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != DAI_TO_USDS:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[0:32])
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if event.amount != amount:
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
                event.notes = f'Receive {amount} USDS from DAI to USDS migration'
                event.address = DAI_TO_USDS_CONTRACT

        return DEFAULT_DECODING_OUTPUT

    def _decode_migrate_mkr(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != MKR_TO_SKY:
            return DEFAULT_DECODING_OUTPUT

        mkr_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        sky_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        user = bytes_to_address(context.tx_log.topics[2])
        mkr_event, sky_event = None, None
        for event in context.decoded_events:
            if (
                event.location_label == user and
                event.amount == mkr_amount and
                event.asset == A_MKR
            ):
                event.counterparty = CPT_SKY
                event.event_type = HistoryEventType.MIGRATE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Migrate {mkr_amount} MKR to SKY'
                mkr_event = event
            elif (
                event.location_label == user and
                event.amount == sky_amount and
                event.asset == SKY_ASSET and
                event.event_type == HistoryEventType.RECEIVE
            ):
                event.counterparty = CPT_SKY
                event.event_type = HistoryEventType.MIGRATE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {sky_amount} SKY from MKR to SKY migration'
                sky_event = event

        if None in (mkr_event, sky_event):
            log.error(f'Failed to decode mkr migration at {context.transaction}')
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events([mkr_event, sky_event], context.decoded_events)
        return DEFAULT_DECODING_OUTPUT

    def _decode_maybe_migrate_dai(self, context: DecoderContext) -> DecodingOutput:
        """Similar to _decode_maybe_downgrade_usds in makerdao decoder, There is no useful log
        event for migrating dai to usds via the migration actions contract. But there is an Exit
        on USDS join which we can use as a hook to check if it is a migration or not"""
        if context.tx_log.topics[0] != EXIT:
            return DEFAULT_DECODING_OUTPUT

        if (
                bytes_to_address(context.tx_log.topics[1]) != MIGRATION_ACTIONS_CONTRACT or
                not self.base.is_tracked(location_label := bytes_to_address(context.tx_log.topics[2]))  # noqa: E501
        ):
            return DEFAULT_DECODING_OUTPUT

        out_event, in_event = None, None
        for event in context.decoded_events:
            if (
                    event.asset == A_DAI and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == MIGRATION_ACTIONS_CONTRACT and
                    event.location_label == location_label
            ):
                out_event = event
                location_label = event.location_label  # type: ignore[assignment]
            elif (
                    event.asset == USDS_ASSET and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == location_label
            ):
                in_event = event
                event.address = MIGRATION_ACTIONS_CONTRACT

        if out_event is None or in_event is None:
            return DEFAULT_DECODING_OUTPUT

        out_event.event_type = HistoryEventType.MIGRATE
        out_event.event_subtype = HistoryEventSubType.SPEND
        out_event.notes = f'Migrate {out_event.amount} DAI to USDS'
        out_event.counterparty = CPT_SKY
        in_event.event_type = HistoryEventType.MIGRATE
        in_event.event_subtype = HistoryEventSubType.RECEIVE
        in_event.notes = f'Receive {in_event.amount} USDS from DAI to USDS migration'
        in_event.counterparty = CPT_SKY
        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            DAI_TO_USDS_CONTRACT: (self._decode_migrate_dai,),
            MKR_TO_SKY_CONTRACT: (self._decode_migrate_mkr,),
            USDS_JOIN_ADDRESS: (self._decode_maybe_migrate_dai,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_SKY, label='Sky', image='sky_money.svg'),)
