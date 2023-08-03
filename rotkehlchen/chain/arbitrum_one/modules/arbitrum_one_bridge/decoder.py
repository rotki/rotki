import logging
from typing import TYPE_CHECKING, Any, Callable

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_CPT_DETAILS, CPT_ARBITRUM_ONE
from rotkehlchen.chain.arbitrum_one.types import ArbitrumOneTransaction
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.user_messages import MessagesAggregator


BRIDGE_ADDRESS = string_to_evm_address('0x0000000000000000000000000000000000000064')
L2_ERC20_GATEWAY = string_to_evm_address('0x09e9222E96E7B4AE2a407B98d48e330053351EEe')
WITHDRAWAL_INITIATED = b'>z\xaf\xa7}\xbf\x18k\x7f\xd4\x88\x00k\xef\xf8\x93tL\xaa<Oo)\x9e\x8ap\x9f\xa2\x08st\xfc'  # noqa: E501
DEPOSIT_TX_TYPE = 100  # A deposit of ETH from L1 to L2 via the Arbitrum bridge.
ERC20_DEPOSIT_FINALIZED = b'\xc7\xf2\xe9\xc5\\@\xa5\x0f\xbc!}\xfcp\xcd9\xa2"\x94\r\xfab\x14Z\xa0\xcaI\xeb\x955\xd4\xfc\xb2'  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ArbitrumOneBridgeDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_eth_erc20_withdraw_event(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a withdraw bridging event. (Sending assets from arbitrum one)"""
        # Check that the event is a bridging event
        if context.tx_log.topics[0] != WITHDRAWAL_INITIATED:
            return DEFAULT_DECODING_OUTPUT

        user_address = context.transaction.from_address

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype != HistoryEventSubType.FEE and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ARBITRUM_ONE
                asset = event.asset
                resolved_asset = self.eth if asset == A_ETH else asset.resolve_to_evm_token()
                event.notes = (
                    f'Bridge {event.balance.amount} {resolved_asset.symbol} from arbitrum_one address '  # noqa: E501
                    f'{user_address} to ethereum address {user_address} via arbitrum_one bridge'
                )

        return DEFAULT_DECODING_OUTPUT

    def _decode_eth_deposit_event(
            self,
            transaction: ArbitrumOneTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Decodes an ETH deposit bridging event (Receiving ETH to arbitrum one)"""
        # Check that the event is a deposit bridging event
        if transaction.tx_type != DEPOSIT_TX_TYPE:
            return decoded_events

        asset = self.eth
        to_address = transaction.to_address

        # Find the corresponding transfer event and update it
        for event in decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.location_label == to_address and
                    event.asset == asset and
                    event.balance.amount == from_wei(FVal(transaction.value))
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = (
                    f'Bridge {event.balance.amount} {asset.symbol} from ethereum address '
                    f'{to_address} to arbitrum_one address {to_address} via arbitrum_one bridge'
                )

        return decoded_events

    def _decode_erc20_deposit_event(self, context: DecoderContext) -> DecodingOutput:
        """Decodes an ERC20 deposit bridging event (Receiving ECR20 tokens to arbitrum one)"""
        if context.tx_log.topics[0] != ERC20_DEPOSIT_FINALIZED:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = hex_or_bytes_to_int(context.tx_log.data[:32])
        user_address = hex_or_bytes_to_address(context.tx_log.topics[3])

        for event in context.decoded_events:
            asset = event.asset
            asset_resolved = self.eth if asset == A_ETH else asset.resolve_to_evm_token()
            amount = asset_normalized_value(raw_amount, asset_resolved)
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.location_label == user_address and
                    event.address == ZERO_ADDRESS and
                    event.balance.amount == amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = (
                    f'Bridge {amount} {asset_resolved.symbol} from ethereum address '
                    f'{user_address} to arbitrum_one address {user_address} via arbitrum_one bridge'  # noqa: E501
                )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            BRIDGE_ADDRESS: (self._decode_eth_erc20_withdraw_event,),
            L2_ERC20_GATEWAY: (self._decode_erc20_deposit_event,),
        }

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_ARBITRUM_ONE: [
                (0, self._decode_eth_deposit_event),  # We need this rule because these transactions contain no logs and consequently we can only run a decoder as a post decoding rule  # noqa: E501
            ],
        }

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_ARBITRUM_ONE: {
            HistoryEventType.DEPOSIT: {
                HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
            },
            HistoryEventType.WITHDRAWAL: {
                HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
            },
        }}

    def counterparties(self) -> list[CounterpartyDetails]:
        return [ARBITRUM_ONE_CPT_DETAILS]
