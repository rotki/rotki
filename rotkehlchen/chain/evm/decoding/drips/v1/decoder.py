import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.drips.v1.constants import (
    COLLECTED,
    CPT_DRIPS,
    DRIPPING,
    GIVEN,
    SPLIT,
    SPLITS_UPDATED,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import bytes_to_address
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Dripsv1CommonDecoder(EvmDecoderInterface, CustomizableDateMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            drips_hub: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        CustomizableDateMixin.__init__(self, base_tools.database)
        self.drips_hub = drips_hub

    def _decode_split(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # always DAI
        )
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_DAI,
            amount=ZERO,
            location_label=user,
            notes=f'Split {amount} DAI from Drips v1 and forward to {bytes_to_address(context.tx_log.topics[2])}',  # noqa: E501
            counterparty=CPT_DRIPS,
            address=context.tx_log.address,
        )
        return DecodingOutput(events=[event])

    def _decode_collected(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        collected_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # always DAI
        )
        split_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # always DAI
        )
        notes = f'Collect {collected_amount} DAI from Drips v1'
        paired_events_data = None
        if split_amount != 0:
            notes += f' and forward {split_amount} DAI to dependencies for splitting'
            split_events = [x for x in context.decoded_events if x.event_type == HistoryEventType.INFORMATIONAL and x.counterparty == CPT_DRIPS]  # noqa: E501
            if len(split_events) == 0:
                log.error(f'Could not find split events for {self.node_inquirer.chain_name} {context.transaction.tx_hash.hex()}')  # noqa: E501
            else:  # count them as an in event pairing so they come after the action item transfer
                paired_events_data = (split_events, False)

        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=A_DAI,
            amount=collected_amount,
            to_event_subtype=HistoryEventSubType.DONATE,
            to_location_label=user,
            to_address=context.tx_log.address,
            to_notes=notes,
            to_counterparty=CPT_DRIPS,
            paired_events_data=paired_events_data,
        )
        return DecodingOutput(action_items=[action_item])

    def _decode_splits_updated(self, context: DecoderContext) -> DecodingOutput:
        contract = self.node_inquirer.contracts.contract(self.drips_hub)
        topic_data, log_data = contract.decode_event(tx_log=context.tx_log, event_name='SplitsUpdated', argument_names=('user', 'receivers'))  # noqa: E501

        if not self.base.is_tracked(user := topic_data[0]):
            return DEFAULT_DECODING_OUTPUT

        initiator = '' if context.transaction.from_address == user else f'{user} '
        for entry in log_data[0]:
            context.decoded_events.append(self.base.make_event_next_index(
                tx_hash=context.transaction.tx_hash,
                timestamp=context.transaction.timestamp,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ZERO,
                location_label=user,
                notes=f'Setup Drips v1 rule to drip {entry[1] / 10000:.2f}% of {initiator}incoming drip funds to {entry[0]}',  # noqa: E501
                counterparty=CPT_DRIPS,
                address=context.tx_log.address,
            ))

        return DEFAULT_DECODING_OUTPUT

    def _decode_given(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        receiver = bytes_to_address(context.tx_log.topics[2])  # receiver does not receive in this transaction  # noqa: E501
        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # always DAI
        )
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.SPEND,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=A_DAI,
            amount=amount,
            to_event_subtype=HistoryEventSubType.DONATE,
            to_location_label=user,
            to_address=context.tx_log.address,
            to_notes=f'Deposit {amount} DAI to Drips v1 as a donation for {receiver}',
            to_counterparty=CPT_DRIPS,
        )
        return DecodingOutput(action_items=[action_item])

    def _decode_dripping(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        receiver = bytes_to_address(context.tx_log.topics[2])  # receiver does not receive in this transaction  # noqa: E501

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # always DAI
        )
        end_ts = Timestamp(int.from_bytes(context.tx_log.data[32:64]))
        new_event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user,
            notes=f'Drip {amount} DAI per second to {receiver} until {self.timestamp_to_date(end_ts)}',  # noqa: E501
            counterparty=CPT_DRIPS,
            address=context.tx_log.address,
        )
        for existing_action_item in context.action_items:
            if existing_action_item.to_event_subtype == HistoryEventSubType.DONATE and existing_action_item.asset == A_DAI and existing_action_item.paired_events_data is not None:  # noqa: E501
                existing_events = existing_action_item.paired_events_data[0]
                existing_action_item.paired_events_data = (existing_events + [new_event], False)  # type: ignore  # can add the sequences
                return DecodingOutput(events=[new_event], action_items=[existing_action_item])

        # else loop found no action item. Create one to match first DAI transfer to
        # the drips hub from the user. Count as in events pairing to guarantee
        # action item transfer comes before all the dripping events
        paired_events_data = ([new_event], False)
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.SPEND,
            from_event_subtype=HistoryEventSubType.NONE,
            location_label=user,
            asset=A_DAI,
            address=self.drips_hub,
            to_event_subtype=HistoryEventSubType.DONATE,
            to_location_label=user,
            to_address=context.tx_log.address,
            to_notes='Deposit {amount} DAI to Drips v1 to start dripping donations',  # noqa: RUF027  # to be filled by the action item
            to_counterparty=CPT_DRIPS,
            paired_events_data=paired_events_data,
        )
        return DecodingOutput(action_items=[action_item], events=[new_event])

    def _decode_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == SPLIT:
            return self._decode_split(context)
        elif context.tx_log.topics[0] == COLLECTED:
            return self._decode_collected(context)
        elif context.tx_log.topics[0] == SPLITS_UPDATED:
            return self._decode_splits_updated(context)
        elif context.tx_log.topics[0] == GIVEN:
            return self._decode_given(context)
        elif context.tx_log.topics[0] == DRIPPING:
            return self._decode_dripping(context)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.drips_hub: (self._decode_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_DRIPS,
            label='Drips',
            image='drips.png',
        ),)
