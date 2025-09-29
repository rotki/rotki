import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from eth_abi import decode as decode_abi

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.scroll.constants import CPT_SCROLL, SCROLL_CPT_DETAILS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

L2_ETH_GATEWAY: Final = string_to_evm_address('0x6EA73e05AdC79974B931123675ea8F78FfdacDF0')
L2_ERC20_GATEWAY: Final = string_to_evm_address('0xE2b4795039517653c5Ae8C2A9BFdd783b48f447A')
# USDC has a special gateway
L2_USDC_GATEWAY: Final = string_to_evm_address('0x33B60d5Dd260d453cAC3782b0bDC01ce84672142')

# Topics
FINALIZE_DEPOSIT_ETH: Final = b'\x9e\x86\xc3V\xe1N$\xe2n<\xe7i\xbf\x8b\x87\xde8\xe0\xfa\xa0\xed\x0c\xa9F\xfa\te\x9a\xa6\x06\xbd-'  # noqa: E501
WITHDRAW_ETH: Final = b'\xd8\xedn\xaa\x9az\x89\x80\xd7\x90\x1e\x91\x1f\xdef\x86\x81\x0b\x98\x9d0\x82\x18-\x1d:=\xf60l\xe2\x0e'  # noqa: E501
FINALIZE_DEPOSIT_ERC20: Final = b'\x16[\xa6\x9fj\xb4\x0cP\xca\xdeoeC\x18\x01\xe5\xf9\xc7\xd7\x83\x0buE9\x19 \xdb\x03\x913\xba4'  # noqa: E501
WITHDRAW_ERC20: Final = b"\xd8\xd3\xa3\xf4\xab\x95iK\xef@GY\x97Y\x8b\xcf\x8a\xcd>\xd9azL\x10\x13yT)AL'\xe8"  # noqa: E501
RELAYED_MESSAGE: Final = b"FA\xdfJ\x96 q\xe1'\x19\xd8\xc8\xc8\xe5\xac\x7f\xc4\xd9{\x92sF\xa3\xd7\xa35\xb1\xf7Q~\x13<"  # noqa: E501

# Method signatures
RELAY_MESSAGE: Final = b'\x8e\xf13.'


class ScrollBridgeDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'ScrollInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def _decode_eth_deposit_withdraw_event(self, context: DecoderContext) -> DecodingOutput:
        """Decodes an ETH deposit or withdraw bridging event
        Ethereum -> Scroll: Withdraw from bridge
        Scroll -> Ethereum: Deposit to bridge
        """
        raw_amount = decode_abi(['uint256'], context.tx_log.data[:32])[0]
        amount = from_wei(FVal(raw_amount))
        if context.tx_log.topics[0] == FINALIZE_DEPOSIT_ETH:
            user_address = bytes_to_address(context.tx_log.topics[2])  # To address
            expected_event_type = HistoryEventType.RECEIVE
            new_event_type = HistoryEventType.WITHDRAWAL
            from_chain, to_chain = ChainID.ETHEREUM, ChainID.SCROLL
        elif context.tx_log.topics[0] == WITHDRAW_ETH:
            user_address = bytes_to_address(context.tx_log.topics[1])  # From address
            expected_event_type = HistoryEventType.SPEND
            new_event_type = HistoryEventType.DEPOSIT
            from_chain, to_chain = ChainID.SCROLL, ChainID.ETHEREUM
        else:
            return DEFAULT_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == user_address and
                event.asset == A_ETH and
                event.amount == amount
            ):
                event.event_type = new_event_type
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_SCROLL
                event.address = L2_ETH_GATEWAY
                event.notes = (
                    f'Bridge {event.amount} ETH from {from_chain.label()} '
                    f'to {to_chain.label()} via Scroll bridge'
                )
                break
        else:
            log.error(f'Could not find ETH {expected_event_type} event for scroll during {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_erc20_deposit_withdraw_event(self, context: DecoderContext) -> DecodingOutput:
        """Decodes an ERC20 deposit or withdraw bridging event
        Ethereum -> Scroll: Withdraw from bridge
        Scroll -> Ethereum: Deposit to bridge
        """
        if (tx_log := context.tx_log).topics[0] not in (FINALIZE_DEPOSIT_ERC20, WITHDRAW_ERC20):
            return DEFAULT_DECODING_OUTPUT

        from_address = bytes_to_address(tx_log.topics[3])
        to_address = bytes_to_address(tx_log.data[:32])

        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_DECODING_OUTPUT

        ethereum_token_address = bytes_to_address(tx_log.topics[1])
        l2_token_address = bytes_to_address(tx_log.topics[2])
        asset = self.base.get_or_create_evm_token(l2_token_address)
        raw_amount = int.from_bytes(tx_log.data[32:64])
        amount = asset_normalized_value(raw_amount, asset)
        expected_event_type, new_event_type, from_chain, to_chain, _ = bridge_prepare_data(
            tx_log=tx_log,
            # The withdraw topic (Scroll to Ethereum) is considered a deposit here
            deposit_topics=(WITHDRAW_ERC20,),
            source_chain=ChainID.SCROLL,
            target_chain=ChainID.ETHEREUM,
            from_address=from_address,
            to_address=to_address,
        )

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == to_address and
                # Address for USDC is the gateway's address
                event.address in (ZERO_ADDRESS, L2_USDC_GATEWAY) and
                event.asset == asset and
                event.amount == amount
            ):
                bridge_match_transfer(
                    event=event,
                    from_address=from_address,
                    to_address=to_address,
                    from_chain=from_chain,
                    to_chain=to_chain,
                    amount=amount,
                    asset=asset,
                    expected_event_type=expected_event_type,
                    new_event_type=new_event_type,
                    counterparty=SCROLL_CPT_DETAILS,
                )

        log.error(
            f'Token receiving event was not found in Scroll for '
            f'{context.transaction.tx_hash.hex()} and L1 token {ethereum_token_address}',
        )

        return DEFAULT_DECODING_OUTPUT

    def _decode_messenger_event(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a relayed message event to a bridge withdrawal"""
        if context.transaction.input_data[:4] != RELAY_MESSAGE:
            return DEFAULT_DECODING_OUTPUT

        method_input_data = context.transaction.input_data[4:]

        from_hex, to_hex, raw_amount = decode_abi(
            ['address', 'address', 'uint256'],
            method_input_data,
        )
        from_address = deserialize_evm_address(from_hex)
        to_address = deserialize_evm_address(to_hex)
        amount = from_wei(FVal(raw_amount))

        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_DECODING_OUTPUT

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == to_address and
                event.asset == A_ETH and
                event.amount == amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_SCROLL
                event.notes = (
                    f'Bridge {amount} ETH from Ethereum to Scroll '
                    f'via Scroll bridge'
                )
                break

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            L2_ETH_GATEWAY: (self._decode_eth_deposit_withdraw_event,),
            L2_USDC_GATEWAY: (self._decode_erc20_deposit_withdraw_event,),
            L2_ERC20_GATEWAY: (self._decode_erc20_deposit_withdraw_event,),
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {
            RELAY_MESSAGE: {
                RELAYED_MESSAGE: self._decode_messenger_event,
            },
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (SCROLL_CPT_DETAILS,)
