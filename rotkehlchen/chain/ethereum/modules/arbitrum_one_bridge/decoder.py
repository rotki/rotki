from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_CPT_DETAILS, CPT_ARBITRUM_ONE
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, ChecksumEvmAddress, DecoderEventMappingType, EvmTokenKind
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.user_messages import MessagesAggregator


BRIDGE_ADDRESS_MAINNET = string_to_evm_address('0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a')
L1_GATEWAY_ROUTER = string_to_evm_address('0x72Ce9c846789fdB6fC1f34aC4AD25Dd9ef7031ef')
ERC20_DEPOSIT_INITIATED = b'\xb8\x91\x0b\x99`\xc4C\xaa\xc3$\x0b\x98XS\x84\xe3\xa6\xf1\t\xfb\xf6\x96\x9e&L?\x18=i\xab\xa7\xe1'  # noqa: E501
ERC20_WITHDRAWAL_FINALIZED = b'\x89\x1a\xfe\x02\x9cu\xc4\xf8\xc5\x85_\xc3H\x05\x98\xbcZSs\x93D\xf6\xaeW[\xdb~\xa2\xa7\x9fV\xb3'  # noqa: E501
MESSAGE_DELIVERED = b'^<\x13\x11\xeaD&d\xe8\xb1a\x1b\xfa\xbe\xf6Y\x12\x0e\xa7\xa0\xa2\xcf\xc0fw\x00\xbe\xbci\xcb\xff\xe1'  # noqa: E501
BRIDGE_CALL_TRIGGERED = b'-\x9d\x11^\xf3\xe4\xa6\x06\xd6\x98\x91;\x1e\xae\x83\x1a<\xdf\xe2\r\x9a\x83\xd4\x80\x07\xb0RgI\xc3\xd4f'  # noqa: E501


class ArbitrumOneBridgeDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_eth_deposit_withdraw(self, context: DecoderContext) -> DecodingOutput:
        """Decodes ETH deposit and withdraw events. (Bridging ETH from and to ethereum)"""
        asset = self.eth
        if context.tx_log.topics[0] == MESSAGE_DELIVERED:  # ETH_DEPOSIT_INITIATED
            amount = from_wei(FVal(context.transaction.value))
            user_address = context.transaction.from_address
            expected_event_type = HistoryEventType.SPEND
            new_event_type = HistoryEventType.DEPOSIT
            expected_location_label = user_address
            from_chain, to_chain = 'ethereum', 'arbitrum_one'
        else:  # ETH_WITHDRAWAL_FINALIZED
            raw_amount = hex_or_bytes_to_int(context.tx_log.data[:32])
            user_address = hex_or_bytes_to_address(context.tx_log.topics[2])
            amount = asset_normalized_value(raw_amount, asset)
            expected_event_type = HistoryEventType.RECEIVE
            new_event_type = HistoryEventType.WITHDRAWAL
            expected_location_label = user_address
            from_chain, to_chain = 'arbitrum_one', 'ethereum'

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                event.asset == asset and
                event.balance.amount == amount
            ):
                event.event_type = new_event_type
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = (
                    f'Bridge {amount} {asset.symbol} from {from_chain} address {user_address} '
                    f'to {to_chain} address {user_address} via arbitrum_one bridge'
                )

        return DEFAULT_DECODING_OUTPUT

    def _decode_erc20_deposit_withdraw(self, tx_log: 'EvmTxReceiptLog', decoded_events: list['EvmEvent']) -> DecodingOutput:  # noqa: E501
        """Decodes ERC20 deposits and withdrawals. (Bridging ERC20 tokens from and to ethereum)"""
        # Read information from event's topics & data
        ethereum_token_address = hex_or_bytes_to_address(tx_log.data[:32])
        asset = EvmToken(evm_address_to_identifier(
            address=ethereum_token_address,
            chain_id=ChainID.ETHEREUM,
            token_type=EvmTokenKind.ERC20,
        ))
        user_address = hex_or_bytes_to_address(tx_log.topics[1])
        raw_amount = hex_or_bytes_to_int(tx_log.data[32:])
        amount = asset_normalized_value(raw_amount, asset)

        # Determine whether it is a deposit or a withdrawal
        if tx_log.topics[0] == ERC20_DEPOSIT_INITIATED:
            expected_event_type = HistoryEventType.SPEND
            expected_location_label = user_address
            new_event_type = HistoryEventType.DEPOSIT
            from_chain, to_chain = 'ethereum', 'arbitrum_one'
        else:  # ERC20_WITHDRAWAL_FINALIZED
            expected_event_type = HistoryEventType.RECEIVE
            expected_location_label = user_address
            new_event_type = HistoryEventType.WITHDRAWAL
            from_chain, to_chain = 'arbitrum_one', 'ethereum'

        # Find the corresponding transfer event and update it
        for event in decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                event.asset == asset and
                event.balance.amount == amount
            ):
                event.event_type = new_event_type
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = (
                    f'Bridge {amount} {asset.symbol} from {from_chain} address {user_address} '
                    f'to {to_chain} address {user_address} via arbitrum_one bridge'
                )
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.asset == self.eth and
                event.address == L1_GATEWAY_ROUTER
            ):
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = (
                    f'Send {event.balance.amount} {self.eth.symbol} '
                    f'to {L1_GATEWAY_ROUTER} for bridging erc20 tokens to arbitrum_one'
                )

        return DEFAULT_DECODING_OUTPUT

    def _decode_asset_deposit_withdraw(self, context: DecoderContext) -> DecodingOutput:
        """Decodes ETH or ERC20 deposit and withdraw events. (Bridging assets from and to ethereum)"""  # noqa: E501
        if context.tx_log.topics[0] in {MESSAGE_DELIVERED, BRIDGE_CALL_TRIGGERED}:
            for tx_log in context.all_logs:  # Check all logs to determine if it is an erc20 event. Eth events have no specific deposit/withdraw topic from which they can be identified.  # noqa: E501
                if tx_log.topics[0] in {ERC20_DEPOSIT_INITIATED, ERC20_WITHDRAWAL_FINALIZED}:
                    return self._decode_erc20_deposit_withdraw(tx_log, context.decoded_events)
            return self._decode_eth_deposit_withdraw(context)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_ARBITRUM_ONE: {
            HistoryEventType.DEPOSIT: {
                HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
            },
            HistoryEventType.RECEIVE: {
                HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
            },
            HistoryEventType.WITHDRAWAL: {
                HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            BRIDGE_ADDRESS_MAINNET: (self._decode_asset_deposit_withdraw,),
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [ARBITRUM_ONE_CPT_DETAILS]
