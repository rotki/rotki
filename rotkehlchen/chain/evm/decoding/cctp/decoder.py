import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.cctp.constants import (
    CCTP_CPT_DETAILS,
    CCTP_DOMAIN_MAPPING,
    CPT_CCTP,
    DEPOSIT_FOR_BURN,
    MESSAGE_RECEIVED,
    MINT_AND_WITHDRAW,
    USDC_DECIMALS,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CctpCommonDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            token_messenger: ChecksumEvmAddress,
            message_transmitter: ChecksumEvmAddress,
            asset_identifier: str,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.token_messenger = token_messenger
        self.message_transmitter = message_transmitter
        self.asset_identifier = asset_identifier

    def _decode_deposit(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[3])):
            return DEFAULT_DECODING_OUTPUT

        to_chain = int.from_bytes(context.tx_log.data[64:96])
        deposit_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=USDC_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == self.asset_identifier and
                event.amount == deposit_amount and
                event.location_label == user_address
            ):
                try:
                    chain_info = f' from {self.evm_inquirer.chain_id.label()} to {CCTP_DOMAIN_MAPPING[to_chain].label()}'  # noqa: E501
                except KeyError:
                    log.error(f'Could not find chain ID {to_chain} for CCTP transfer from {self.evm_inquirer.chain_name}')  # noqa: E501
                    chain_info = ''
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.notes = f'Bridge {event.amount} USDC{chain_info} via CCTP'
                event.counterparty = CPT_CCTP
                break
        else:
            log.error(f'Could not find matching spend event for {self.evm_inquirer.chain_name} CCTP bridge deposit {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_withdraw(self, context: DecoderContext) -> DecodingOutput:
        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_DECODING_OUTPUT

        deposit_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=USDC_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == self.asset_identifier and
                event.amount == deposit_amount and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.notes = f'Bridge {event.amount} USDC via CCTP'
                event.counterparty = CPT_CCTP
                break
        else:
            log.error(f'Could not find matching receive event for {self.evm_inquirer.chain_name} CCTP bridge withdrawal {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_message_received(self, context: DecoderContext) -> DecodingOutput:
        """Adds chain information to the event notes for the withdrawals."""
        if context.tx_log.topics[0] != MESSAGE_RECEIVED:
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.WITHDRAWAL and
                event.event_subtype == HistoryEventSubType.BRIDGE and
                event.counterparty == CPT_CCTP
            ):
                from_chain = int.from_bytes(context.tx_log.data[:32])
                try:
                    chain_info = f' from {CCTP_DOMAIN_MAPPING[from_chain].label()} to {self.evm_inquirer.chain_id.label()}'  # noqa: E501
                    event.notes = f'Bridge {event.amount} USDC{chain_info} via CCTP'
                except KeyError:
                    log.error(f'Could not find chain ID {from_chain} for CCTP transfer to {self.evm_inquirer.chain_name}')  # noqa: E501
                break
        else:
            log.error(f'Could not find matching withdrawal event for {self.evm_inquirer.chain_name} CCTP bridge chain information {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_bridge(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT_FOR_BURN:
            return self._decode_deposit(context)

        if context.tx_log.topics[0] == MINT_AND_WITHDRAW:
            return self._decode_withdraw(context)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CCTP_CPT_DETAILS,)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.token_messenger: (self._decode_bridge,),
            self.message_transmitter: (self._decode_message_received,),
        }
