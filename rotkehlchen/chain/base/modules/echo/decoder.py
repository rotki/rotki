import logging
from typing import TYPE_CHECKING, Any

from collections.abc import Callable

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value_decimals
from rotkehlchen.chain.base.modules.echo.constants import (
    FUNDING_CONDUIT,
    FUNDER_REGISTRY,
    FUNDER_DEREGISTERED,
    DEAL_ABI,
    DEAL_FUNDED,
    DEAL_REFUNDED,
    CPT_ECHO,
    ECHO_CPT_DETAILS,
    FEE_PAID,
    POOL_REFUNDED
)
from rotkehlchen.chain.evm.decoding.cctp.constants import (
    USDC_DECIMALS
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    ActionItem,
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)

from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, EvmTokenKind
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
        if not self.base.is_tracked(bytes_to_address(context.tx_log.topics[1])):
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
    
    def _mark_for_refund(self, context: DecoderContext) -> DecodingOutput:
        if not context.tx_log.topics[0] == FUNDER_DEREGISTERED:
            return DEFAULT_DECODING_OUTPUT
        user_address = bytes_to_address(context.tx_log.topics[2])
        if not self.base.is_tracked(user_address):
            return DEFAULT_DECODING_OUTPUT
        for _log in context.all_logs:
            if (
                _log.topics[0] == POOL_REFUNDED and
                user_address == bytes_to_address(_log.topics[2])
            ):
                raw_token_address = self.evm_inquirer.call_contract(
                    contract_address=_log.address,
                    abi=DEAL_ABI,
                    method_name='token'
                )
                token = EvmToken(evm_address_to_identifier(raw_token_address, self.evm_inquirer.chain_id, EvmTokenKind.ERC20))
                token_amount = int.from_bytes(_log.data[:32])
                amount = asset_normalized_value(token_amount, token)
                context.action_items.append(ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.RECEIVE,
                    from_event_subtype=HistoryEventSubType.NONE,
                    to_event_type=HistoryEventType.WITHDRAWAL,
                    to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
                    asset=token,
                    amount=amount,
                    location_label=user_address,
                    address=_log.address,
                    to_counterparty=CPT_ECHO,
                    to_notes=f'Refund {amount} USDC from {_log.address} on Echo'
                ))
                break
        return DEFAULT_DECODING_OUTPUT
        
    def _process_funding(
            self,
            transaction: 'EvmTransaction',  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        fund_amount = None
        deal_address = None
        user_address = None
        for tx_log in all_logs:
            if(
                tx_log.topics[0] == DEAL_FUNDED and
                self.base.is_tracked(user_address := bytes_to_address(tx_log.topics[2]))
            ):
                fund_amount = int.from_bytes(tx_log.data[0:32])
                deal_address = tx_log.address
                break

        for event in decoded_events:
            if(
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == asset_normalized_value(fund_amount, event.asset)
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.location_label = user_address
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
            FUNDER_REGISTRY: (self._mark_for_refund,),
        }
    
    def addresses_to_counterparties(self) -> dict['ChecksumEvmAddress', str]:
        return {FUNDING_CONDUIT: CPT_ECHO}
    
    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_ECHO: [(0, self._process_funding)],
        }