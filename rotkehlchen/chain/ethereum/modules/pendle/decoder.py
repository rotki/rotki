import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.pendle.constants import CPT_PENDLE
from rotkehlchen.chain.evm.decoding.pendle.decoder import PendleCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

from .constants import (
    NEW_LOCK_POSITION_TOPIC,
    PENDLE_TOKEN,
    VE_PENDLE_CONTRACT_ADDRESS,
    WITHDRAW_TOPIC,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PendleDecoder(PendleCommonDecoder, CustomizableDateMixin):
    """Ethereum-specific Pendle decoder.

    On Ethereum, Pendle has additional contracts and logic related to
    vote-escrowed PENDLE (vePENDLE), which are not present on other chains.
    """

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        CustomizableDateMixin.__init__(self, base_tools.database)

    def _decode_ve_pendle_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == NEW_LOCK_POSITION_TOPIC:
            refund_event = None
            for event in context.decoded_events:
                # we don't compare the amount because it is the total amount locked that is emitted
                # and not the amount that was currently deposited to be locked.
                if (
                        event.address == VE_PENDLE_CONTRACT_ADDRESS and
                        event.asset == PENDLE_TOKEN and
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
                        event.address == VE_PENDLE_CONTRACT_ADDRESS and
                        event.asset == A_ETH and
                        event.event_type == HistoryEventType.RECEIVE and
                        event.event_subtype == HistoryEventSubType.NONE
                ):
                    refund_event = event

                elif (
                    event.address == VE_PENDLE_CONTRACT_ADDRESS and
                    event.asset == A_ETH and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    # vePendle ETH fee events always appear before the lock event.
                    # We capture the refund (if any) first and adjust the fee amount accordingly.
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
                    event.address == VE_PENDLE_CONTRACT_ADDRESS and
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

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            VE_PENDLE_CONTRACT_ADDRESS: (self._decode_ve_pendle_events,),
        }
