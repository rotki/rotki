import logging
from typing import TYPE_CHECKING, Any

from collections.abc import Callable

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.base.modules.echo.constants import (
    FUNDING_CONDUIT,
    DEAL_FUNDED,
    DEAL_REFUNDED,
    CPT_ECHO,
    ECHO_CPT_DETAILS,
    FEE_PAID
)
from rotkehlchen.chain.evm.decoding.cctp.constants import (
    USDC_DECIMALS
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)

from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, Location
from rotkehlchen.utils.misc import bytes_to_address
if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EchoDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator') -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator
        )

    def _decode_fee_paid(self, context: DecoderContext) -> DecodingOutput:
        if not context.tx_log.topics[0] == FEE_PAID:
            return DEFAULT_DECODING_OUTPUT
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT
        
        for event in context.decoded_events:
            if(
                event.sequence_index == context.tx_log.log_index - 1 and
                event.event_type == HistoryEventType.INFORMATIONAL and
                event.event_subtype == HistoryEventSubType.APPROVE
            ):
                fee_amount = token_normalized_value_decimals(
                    token_amount=int.from_bytes(context.tx_log.data[0:32]),
                    token_decimals=USDC_DECIMALS # Echo is using USDC for now
                )
                new_event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=event.asset,
                    balance=Balance(amount=fee_amount),
                    address=FUNDING_CONDUIT,
                    notes=f'Paid {fee_amount} USDC as part of funding an Echo deal',
                    counterparty=CPT_ECHO
                )
                context.decoded_events.append(new_event)
                break
        return DEFAULT_DECODING_OUTPUT
        
    def _process_funding(
            self,
            transaction: 'EvmTransaction',  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        log.debug('post process', decoded_events, all_logs)
        fund_amount = None
        deal_address = None
        for event in all_logs:
            if(
                event.topics[0] == DEAL_FUNDED and
                self.base.is_tracked(user_address := bytes_to_address(event.tx_log.topics[1]))
            ):
                fund_amount = bytes_to_address(event.data[0:32])
                deal_address = event.address
                break
        for event in decoded_events:
            if(
                event.event_type == HistoryEventType.SPEND and
                event.balance.amount == fund_amount
            ):
                event.address = deal_address
                event.counterparty = CPT_ECHO
                event.notes = f'Fund {event.balance.amount} {event.asset.symbol_or_name()} to {deal_address} on Echo'
                break
        return decoded_events

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ECHO_CPT_DETAILS, )
    
    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            FUNDING_CONDUIT: (self._decode_fee_paid,),
        }
    
    def addresses_to_counterparties(self) -> dict['ChecksumEvmAddress', str]:
        return dict.fromkeys(FUNDING_CONDUIT, CPT_ECHO)
    
    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_ECHO: [(0, self._process_funding)],
        }