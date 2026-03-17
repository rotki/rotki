import logging
from typing import Any

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_DAI, A_MKR, A_USDC
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    BUY_GEM,
    CPT_SKY,
    DAI_TO_USDS,
    DAI_TO_USDS_CONTRACT,
    EXIT,
    LITE_PSM_USDC_A,
    MIGRATION_ACTIONS_CONTRACT,
    MKR_TO_SKY,
    MKR_TO_SKY_CONTRACT,
    SELL_GEM,
    SKY_ASSET,
    USDS_ASSET,
    USDS_JOIN_ADDRESS,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SkyDecoder(EvmDecoderInterface):
    """Decoder for Sky ecosystem migration events.

    This decoder handles the migration of MakerDAO assets to the Sky ecosystem:

    • DAI to USDS migrations - Direct migrations using the DAI_TO_USDS_CONTRACT
    • MKR to SKY migrations - Token migrations using the MKR_TO_SKY_CONTRACT
    • Indirect DAI to USDS migrations - Via the MIGRATION_ACTIONS_CONTRACT using USDS join exit events
    """  # noqa: E501

    def _decode_migrate_dai(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != DAI_TO_USDS:
            return DEFAULT_EVM_DECODING_OUTPUT

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

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_migrate_mkr(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != MKR_TO_SKY:
            return DEFAULT_EVM_DECODING_OUTPUT

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
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events([mkr_event, sky_event], context.decoded_events)
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_maybe_migrate_dai(self, context: DecoderContext) -> EvmDecodingOutput:
        """Similar to _decode_maybe_downgrade_usds in makerdao decoder, There is no useful log
        event for migrating dai to usds via the migration actions contract. But there is an Exit
        on USDS join which we can use as a hook to check if it is a migration or not"""
        if context.tx_log.topics[0] != EXIT:
            return DEFAULT_EVM_DECODING_OUTPUT

        if (
                bytes_to_address(context.tx_log.topics[1]) != MIGRATION_ACTIONS_CONTRACT or
                not self.base.is_tracked(location_label := bytes_to_address(context.tx_log.topics[2]))  # noqa: E501
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

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
                location_label = event.location_label
            elif (
                    event.asset == USDS_ASSET and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == location_label
            ):
                in_event = event
                event.address = MIGRATION_ACTIONS_CONTRACT

        if out_event is None or in_event is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        out_event.event_type = HistoryEventType.MIGRATE
        out_event.event_subtype = HistoryEventSubType.SPEND
        out_event.notes = f'Migrate {out_event.amount} DAI to USDS'
        out_event.counterparty = CPT_SKY
        in_event.event_type = HistoryEventType.MIGRATE
        in_event.event_subtype = HistoryEventSubType.RECEIVE
        in_event.notes = f'Receive {in_event.amount} USDS from DAI to USDS migration'
        in_event.counterparty = CPT_SKY
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_direct_psm_swap(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in (BUY_GEM, SELL_GEM):
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        if context.tx_log.topics[0] == BUY_GEM:
            spend_asset, receive_asset = A_DAI, A_USDC
        else:
            spend_asset, receive_asset = A_USDC, A_DAI

        out_event, in_event = None, None
        for event in context.decoded_events:
            if (
                    out_event is None and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == spend_asset and
                    event.location_label == user_address
            ):
                out_event = event
            elif (
                    in_event is None and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == receive_asset and
                    event.location_label == user_address
            ):
                in_event = event

        if out_event is None or in_event is None:
            log.error(f'Failed to decode direct PSM swap at {context.transaction}')
            return DEFAULT_EVM_DECODING_OUTPUT

        out_event.event_type = HistoryEventType.TRADE
        out_event.event_subtype = HistoryEventSubType.SPEND
        out_event.notes = f'Swap {out_event.amount} {out_event.asset.resolve_to_asset_with_symbol().symbol} in Sky PSM'  # noqa: E501
        out_event.counterparty = CPT_SKY
        out_event.address = LITE_PSM_USDC_A
        in_event.event_type = HistoryEventType.TRADE
        in_event.event_subtype = HistoryEventSubType.RECEIVE
        in_event.notes = f'Receive {in_event.amount} {in_event.asset.resolve_to_asset_with_symbol().symbol} from Sky PSM swap'  # noqa: E501
        in_event.counterparty = CPT_SKY
        in_event.address = LITE_PSM_USDC_A
        maybe_reshuffle_events([out_event, in_event], context.decoded_events)
        return EvmDecodingOutput(process_swaps=True)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            DAI_TO_USDS_CONTRACT: (self._decode_migrate_dai,),
            MKR_TO_SKY_CONTRACT: (self._decode_migrate_mkr,),
            USDS_JOIN_ADDRESS: (self._decode_maybe_migrate_dai,),
            LITE_PSM_USDC_A: (self._decode_direct_psm_swap,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_SKY, label='Sky', image='sky_money.svg'),)
