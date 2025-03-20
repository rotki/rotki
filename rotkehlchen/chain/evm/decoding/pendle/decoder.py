import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
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
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .constants import CPT_PENDLE, NEW_LOCK_POSITION_TOPIC, WITHDRAW_TOPIC

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PendleCommonDecoder(DecoderInterface, CustomizableDateMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pendle_token: 'Asset',
            ve_pendle_contract: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        CustomizableDateMixin.__init__(self, base_tools.database)
        self.pendle_token = pendle_token
        self.ve_pendle_contract = ve_pendle_contract

    def _decode_ve_pendle_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == NEW_LOCK_POSITION_TOPIC:
            refund_event = None
            for event in context.decoded_events:
                # we don't compare the amount because it is the total amount locked that is emitted
                # and not the amount that was currently deposited to be locked.
                if (
                        event.address == self.ve_pendle_contract and
                        event.asset == self.pendle_token and
                        event.event_type == HistoryEventType.SPEND and
                        event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.notes = f'Lock {event.amount} PENDLE in voting escrow until {self.timestamp_to_date(lock_time := deserialize_timestamp(int.from_bytes(context.tx_log.data[32:64])))}'  # noqa: E501
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.extra_data = {'lock_time': lock_time}
                    event.counterparty = CPT_PENDLE
                    break

                elif (
                        event.address == self.ve_pendle_contract and
                        event.asset == A_ETH and
                        event.event_type == HistoryEventType.RECEIVE and
                        event.event_subtype == HistoryEventSubType.NONE
                ):
                    refund_event = event

                elif (
                    event.address == self.ve_pendle_contract and
                    event.asset == A_ETH and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.counterparty = CPT_PENDLE
                    event.event_subtype = HistoryEventSubType.FEE
                    event.amount = (amount := event.amount if refund_event is None else event.amount - refund_event.amount)  # noqa: E501
                    event.notes = f'Pay {amount} ETH as vePendle state broadcast fee'

            else:
                log.error(f'Could not find pendle lock transfer for transaction {context.transaction}')  # noqa: E501

            if refund_event is not None:
                context.decoded_events.remove(refund_event)

        elif context.tx_log.topics[0] == WITHDRAW_TOPIC:
            amount = token_normalized_value_decimals(
                token_amount=int.from_bytes(context.tx_log.data[:32]),
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )
            for event in context.decoded_events:
                if (
                    event.amount == amount and
                    event.address == self.ve_pendle_contract and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.counterparty = CPT_PENDLE
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.notes = f'Withdraw {amount} PENDLE from vote escrow'
                    break
            else:
                log.error(f'Could not find pendle unlock transfer for transaction {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.ve_pendle_contract: (self._decode_ve_pendle_events,)}

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_PENDLE,
            label='Pendle Finance',
            image='pendle_light.svg',
            darkmode_image='pendle_dark.svg',
        ),)
