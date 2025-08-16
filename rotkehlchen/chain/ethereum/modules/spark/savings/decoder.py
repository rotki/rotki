import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.sky.constants import (
    CPT_SKY,
    MIGRATION_ACTIONS_CONTRACT,
    SUSDS_ASSET,
    SUSDS_CONTRACT,
)
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
    DEPOSIT_TOPIC,
    WITHDRAW_TOPIC_V3,
)
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.chain.evm.decoding.spark.savings.decoder import SparksavingsCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_SDAI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SparksavingsDecoder(SparksavingsCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            spark_savings_tokens=(
                string_to_evm_address('0xBc65ad17c5C0a2A4D159fa5a503f4992c7B545FE'),  # sUSDC
                string_to_evm_address('0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),  # sUSDS
                string_to_evm_address('0x83F20F44975D03b1b09e64809B757c47f942BEeA'),  # sDAI
            ),
        )
        self.sdai = A_SDAI.resolve_to_evm_token()

    def _decode_sky_migration_to_susds(self, context: DecoderContext) -> DecodingOutput:
        """Decodes Sky protocol migrations from sDAI/DAI to sUSDS tokens.

        This belongs in the Sky decoder but lives here because our address-to-decoder
        mapping only allows one function per address. Having it in both decoders would
        cause one to overwrite the other. Since sUSDS is a Spark Savings token, it
        makes sense to keep it here.
        """
        if not (
            (is_deposit := context.tx_log.topics[0] == DEPOSIT_TOPIC) or
            context.tx_log.topics[0] == WITHDRAW_TOPIC_V3
        ):
            return DEFAULT_DECODING_OUTPUT

        if (assets_amount := token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )) == ZERO:
            return DEFAULT_DECODING_OUTPUT

        shares_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        received_address = bytes_to_address(context.tx_log.topics[2])
        action_items = []
        if is_deposit:
            action_items.append(ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=SUSDS_ASSET,
                amount=shares_amount,
                to_event_type=HistoryEventType.MIGRATE,
                to_event_subtype=HistoryEventSubType.RECEIVE,
                to_counterparty=CPT_SKY,
                to_notes=f'Receive {shares_amount} sUSDS ({assets_amount} USDS) from sDAI to sUSDS migration',  # noqa: E501
                extra_data={'underlying_amount': str(assets_amount)},
                to_address=MIGRATION_ACTIONS_CONTRACT,
            ))

        # Try to find sDAI withdraw log to create sDAI spend event
        for tx_log in context.all_logs:
            if (
                    tx_log.topics[0] == WITHDRAW_TOPIC_V3 and
                    tx_log.address == self.sdai.evm_address and
                    bytes_to_address(tx_log.topics[1]) == MIGRATION_ACTIONS_CONTRACT and
                    bytes_to_address(tx_log.topics[3]) == received_address
            ):

                sdai_shares_amount = token_normalized_value_decimals(
                    token_amount=int.from_bytes(tx_log.data[32:64]),
                    token_decimals=DEFAULT_TOKEN_DECIMALS,
                )
                underlying_dai_amount = token_normalized_value_decimals(
                    token_amount=int.from_bytes(tx_log.data[:32]),
                    token_decimals=DEFAULT_TOKEN_DECIMALS,
                )

                # Create sDAI spend event
                sdai_event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=tx_log,
                    event_type=HistoryEventType.MIGRATE,
                    event_subtype=HistoryEventSubType.SPEND,
                    asset=self.sdai,
                    amount=sdai_shares_amount,
                    location_label=received_address,
                    notes=f'Migrate {sdai_shares_amount} sDAI ({underlying_dai_amount} DAI) to sUSDS',  # noqa: E501
                    counterparty=CPT_SKY,
                    address=MIGRATION_ACTIONS_CONTRACT,
                    extra_data={'underlying_amount': str(underlying_dai_amount)},
                )
                return DecodingOutput(action_items=action_items, events=[sdai_event])

        # If no sDAI withdraw log found, try DAI -> sUSDS migration
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_DAI and
                    event.location_label == received_address
            ):  # DAI -> sUSDS
                action_items[0].to_notes = f'Receive {shares_amount} sUSDS ({assets_amount} USDS) from DAI to sUSDS migration'  # noqa: E501
                event.event_type = HistoryEventType.MIGRATE
                event.event_subtype = HistoryEventSubType.SPEND
                event.address = MIGRATION_ACTIONS_CONTRACT
                event.notes = f'Migrate {event.amount} DAI to sUSDS'
                event.counterparty = CPT_SKY
                return DecodingOutput(action_items=action_items)

        # If neither sDAI nor DAI event found, log error
        log.error(f'Could not find the deposit sDAI event in {context.transaction}')
        return DEFAULT_DECODING_OUTPUT

    def _decode_sdai_events(self, context: DecoderContext) -> DecodingOutput:
        """Decodes sDAI deposit and withdrawal events for Spark Savings.

        Creates corresponding sDAI events for deposit/withdrawal transactions
        and ensures proper event ordering.
        """
        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            owner_address = bytes_to_address(context.tx_log.topics[2])
            event_type = HistoryEventType.RECEIVE
            event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            notes = f'Receive {asset_normalized_value(amount=int.from_bytes(context.tx_log.data[32:64]), asset=self.sdai)} sDAI from depositing into Spark Savings'  # noqa: E501
        else:  # withdraw topic
            owner_address = bytes_to_address(context.tx_log.topics[2])
            event_type = HistoryEventType.SPEND
            event_subtype = HistoryEventSubType.RETURN_WRAPPED
            notes = f'Return {asset_normalized_value(amount=int.from_bytes(context.tx_log.data[32:64]), asset=self.sdai)} sDAI to Spark Savings'  # noqa: E501

        if (amount := asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=self.sdai,
        )) == ZERO:
            return DEFAULT_DECODING_OUTPUT

        in_event = out_event = None
        for event in context.decoded_events:
            if event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED:
                out_event = event
            elif event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED:
                in_event = event

        # create the corresponding sDAI event
        transfer = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=self.sdai,
            amount=amount,
            location_label=owner_address,
            notes=notes,
            address=self.sdai.evm_address,
            counterparty=CPT_SPARK,
        )

        # order events correctly based on the transaction type
        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            maybe_reshuffle_events(
                ordered_events=[out_event, transfer],
                events_list=context.decoded_events,
            )
        else:
            maybe_reshuffle_events(
                ordered_events=[transfer, in_event],
                events_list=context.decoded_events,
            )

        return DecodingOutput(events=[transfer])

    def _decode_spark_tokens_deposit_withdrawal(self, context: DecoderContext) -> DecodingOutput:
        """Decodes deposit and withdrawal events for Spark tokens on Ethereum.

        Handles sky migration events specifically for Ethereum and delegates
        to specialized decoders for sDAI and sUSDS tokens.
        """
        if (  # Check if this is a sky migration event and delegate to the migration decoder
            context.tx_log.address == SUSDS_CONTRACT and
            context.tx_log.topics[0] in (DEPOSIT_TOPIC, WITHDRAW_TOPIC_V3) and
            bytes_to_address(context.tx_log.topics[1]) == MIGRATION_ACTIONS_CONTRACT
        ):
            return self._decode_sky_migration_to_susds(context)

        result = super()._decode_spark_tokens_deposit_withdrawal(context)
        if (  # For sDAI, we need special handling to add the additional sDAI event
            context.tx_log.address == self.sdai.evm_address and
            bytes_to_address(context.tx_log.topics[1]) != MIGRATION_ACTIONS_CONTRACT
        ):
            return self._decode_sdai_events(context)

        return result
