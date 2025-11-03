import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_CPT_DETAILS, CPT_ARBITRUM_ONE
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


OLD_BRIDGE_ADDRESS_MAINNET: Final = string_to_evm_address('0x011B6E24FfB0B5f5fCc564cf4183C5BBBc96D515')  # noqa: E501
BRIDGE_ADDRESS_MAINNET: Final = string_to_evm_address('0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a')
L1_GATEWAY_ROUTER: Final = string_to_evm_address('0x72Ce9c846789fdB6fC1f34aC4AD25Dd9ef7031ef')
DELAYED_INBOX: Final = string_to_evm_address('0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f')
ERC20_DEPOSIT_INITIATED: Final = b'\xb8\x91\x0b\x99`\xc4C\xaa\xc3$\x0b\x98XS\x84\xe3\xa6\xf1\t\xfb\xf6\x96\x9e&L?\x18=i\xab\xa7\xe1'  # noqa: E501
ERC20_WITHDRAWAL_FINALIZED: Final = b'\x89\x1a\xfe\x02\x9cu\xc4\xf8\xc5\x85_\xc3H\x05\x98\xbcZSs\x93D\xf6\xaeW[\xdb~\xa2\xa7\x9fV\xb3'  # noqa: E501
MESSAGE_DELIVERED: Final = b'^<\x13\x11\xeaD&d\xe8\xb1a\x1b\xfa\xbe\xf6Y\x12\x0e\xa7\xa0\xa2\xcf\xc0fw\x00\xbe\xbci\xcb\xff\xe1'  # noqa: E501
INBOX_MESSAGE_DELIVERED: Final = b'\xffd\x90_s\xa6\x7f\xb5\x94\xe0\xf9@\xa8\x07Z\x86\r\xb4\x89\xad\x99\x1e\x03/H\xc8\x11#\xebR\xd6\x0b'  # noqa: E501
BRIDGE_CALL_TRIGGERED: Final = b'-\x9d\x11^\xf3\xe4\xa6\x06\xd6\x98\x91;\x1e\xae\x83\x1a<\xdf\xe2\r\x9a\x83\xd4\x80\x07\xb0RgI\xc3\xd4f'  # noqa: E501


class ArbitrumOneBridgeDecoder(EvmDecoderInterface):
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
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_eth_deposit_withdraw(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes ETH deposit and withdraw events. (Bridging ETH from and to ethereum)"""
        if context.tx_log.topics[0] == INBOX_MESSAGE_DELIVERED:  # ETH_DEPOSIT_INITIATED
            # data here is abi.encodePacked(dest, msg.value).
            # couldn't find a proper way to decode abi packed, so reverse engineered
            # this one. TODO: We may need it in other places so if we find a proper
            # library replace the shit below.
            #
            # It has 2 int as 32-bytes packed first, which are the offsets for the other two
            # and then has two more 32-bytes which are the address and the msg.value
            value_offset = int.from_bytes(context.tx_log.data[:32])
            address_offset = int.from_bytes(context.tx_log.data[32:64])
            user_address = bytes_to_address(context.tx_log.data[address_offset:address_offset + 32])  # noqa: E501
            raw_amount = int.from_bytes(context.tx_log.data[address_offset + value_offset:address_offset + value_offset + 32])  # noqa: E501

            amount = from_wei(FVal(raw_amount))
            expected_event_type = HistoryEventType.SPEND
            new_event_type = HistoryEventType.DEPOSIT
            from_chain, to_chain = ChainID.ETHEREUM, ChainID.ARBITRUM_ONE
        else:  # ETH_WITHDRAWAL_FINALIZED
            raw_amount = int.from_bytes(context.tx_log.data[:32])
            user_address = bytes_to_address(context.tx_log.topics[2])
            amount = from_wei(FVal(raw_amount))
            expected_event_type = HistoryEventType.RECEIVE
            new_event_type = HistoryEventType.WITHDRAWAL
            from_chain, to_chain = ChainID.ARBITRUM_ONE, ChainID.ETHEREUM

        if not self.base.is_tracked(user_address):
            return DEFAULT_EVM_DECODING_OUTPUT

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == user_address and
                event.asset == self.eth and
                event.amount == amount
            ):
                event.event_type = new_event_type
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = (
                    f'Bridge {amount} ETH from {from_chain.label()} '
                    f'to {to_chain.label()} via Arbitrum One bridge'
                )
                break

        else:
            log.error(f'Could not find ETH {expected_event_type} for arbitrum one during {context.transaction.tx_hash!s}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_erc20_deposit_withdraw(self, tx_log: 'EvmTxReceiptLog', decoded_events: list['EvmEvent']) -> EvmDecodingOutput:  # noqa: E501
        """Decodes ERC20 deposits and withdrawals. (Bridging ERC20 tokens from and to ethereum)"""
        from_address = bytes_to_address(tx_log.topics[1])
        to_address = bytes_to_address(tx_log.topics[2])

        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_EVM_DECODING_OUTPUT

        ethereum_token_address = bytes_to_address(tx_log.data[:32])
        asset = self.base.get_or_create_evm_token(ethereum_token_address)
        raw_amount = int.from_bytes(tx_log.data[32:])
        amount = asset_normalized_value(raw_amount, asset)

        expected_event_type, new_event_type, from_chain, to_chain, _ = bridge_prepare_data(
            tx_log=tx_log,
            deposit_topics=(ERC20_DEPOSIT_INITIATED,),
            source_chain=ChainID.ETHEREUM,
            target_chain=ChainID.ARBITRUM_ONE,
            from_address=from_address,
            to_address=to_address,
        )

        # Find the corresponding transfer event and update it
        for event in decoded_events:
            if (
                event.event_type == expected_event_type and
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
                    counterparty=ARBITRUM_ONE_CPT_DETAILS,
                )
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.asset == self.eth and
                event.address == L1_GATEWAY_ROUTER
            ):
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = (
                    f'Spend {event.amount} ETH to bridge ERC20 tokens to Arbitrum One'
                )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_asset_deposit_withdraw(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes ETH or ERC20 deposit and withdraw events. (Bridging assets from and to ethereum)"""  # noqa: E501
        if context.tx_log.topics[0] in {MESSAGE_DELIVERED, INBOX_MESSAGE_DELIVERED, BRIDGE_CALL_TRIGGERED}:  # noqa: E501
            for tx_log in context.all_logs:  # Check all logs to determine if it is an erc20 event. Eth events have no specific deposit/withdraw topic from which they can be identified.  # noqa: E501
                if tx_log.topics[0] in {ERC20_DEPOSIT_INITIATED, ERC20_WITHDRAWAL_FINALIZED}:
                    return self._decode_erc20_deposit_withdraw(tx_log, context.decoded_events)
            return self._decode_eth_deposit_withdraw(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            DELAYED_INBOX: (self._decode_eth_deposit_withdraw,),
            BRIDGE_ADDRESS_MAINNET: (self._decode_asset_deposit_withdraw,),
            OLD_BRIDGE_ADDRESS_MAINNET: (self._decode_asset_deposit_withdraw,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ARBITRUM_ONE_CPT_DETAILS,)
