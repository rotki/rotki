import logging
from typing import TYPE_CHECKING, Any, Final
from eth_abi import decode as decode_abi

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import (
    bridge_match_transfer,
    bridge_prepare_data,
    maybe_reshuffle_events,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.scroll.constants import CPT_SCROLL, SCROLL_CPT_DETAILS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# https://docs.scroll.io/en/developers/scroll-contracts/
L1_GATEWAY_ROUTER: Final = string_to_evm_address('0xF8B1378579659D8F7EE5f3C929c2f3E332E41Fd6')
L1_ETH_GATEWAY_PROXY: Final = string_to_evm_address('0x7F2b8C31F88B6006c382775eea88297Ec1e3E905')
L1_ERC20_GATEWAY: Final = string_to_evm_address('0xD8A791fE2bE73eb6E6cF1eb0cb3F36adC9B3F8f9')
L1_USDC_GATEWAY: Final = string_to_evm_address('0xf1AF3b23DE0A5Ca3CAb7261cb0061C0D779A5c7B')
L1_MESSENGER_PROXY: Final = string_to_evm_address('0x6774Bcbd5ceCeF1336b5300fb5186a12DDD8b367')

# DepositETH - 0x6670de856ec8bf5cb2b7e957c5dc24759716056f79d97ea5e7c939ca0ba5a675
DEPOSIT_ETH: Final = b'fp\xde\x85n\xc8\xbf\\\xb2\xb7\xe9W\xc5\xdc$u\x97\x16\x05oy\xd9~\xa5\xe7\xc99\xca\x0b\xa5\xa6u'  # noqa: E501
# FinalizeWithdrawETH - 0x96db5d1cee1dd2760826bb56fabd9c9f6e978083e0a8b88559c741a29e9746e7
FINALIZE_WITHDRAW_ETH: Final = b'\x96\xdb]\x1c\xee\x1d\xd2v\x08&\xbbV\xfa\xbd\x9c\x9fn\x97\x80\x83\xe0\xa8\xb8\x85Y\xc7A\xa2\x9e\x97F\xe7'  # noqa: E501
# SentMessage - 0x104371f3b442861a2a7b82a070afbbaab748bb13757bf47769e170e37809ec1e
SENT_MESSAGE: Final = b'\x10Cq\xf3\xb4B\x86\x1a*{\x82\xa0p\xaf\xbb\xaa\xb7H\xbb\x13u{\xf4wi\xe1p\xe3x\t\xec\x1e'  # noqa: E501

# DepositERC20 - 0x31cd3b976e4d654022bf95c68a2ce53f1d5d94afabe0454d2832208eeb40af25
DEPOSIT_ERC20: Final = b'1\xcd;\x97nMe@"\xbf\x95\xc6\x8a,\xe5?\x1d]\x94\xaf\xab\xe0EM(2 \x8e\xeb@\xaf%'  # noqa: E501
# FinalizeWithdrawERC20 - 0xc6f985873b37805705f6bce756dce3d1ff4b603e298d506288cce499926846a7
FINALIZE_WITHDRAW_ERC20: Final = b'\xc6\xf9\x85\x87;7\x80W\x05\xf6\xbc\xe7V\xdc\xe3\xd1\xffK`>)\x8dPb\x88\xcc\xe4\x99\x92hF\xa7'  # noqa: E501


class ScrollBridgeDecoder(DecoderInterface):
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
        if context.tx_log.topics[0] == DEPOSIT_ETH:
            raw_amount = decode_abi(['uint256'], context.tx_log.data)[0]
            user_address = hex_or_bytes_to_address(context.tx_log.topics[1])
            amount = from_wei(FVal(raw_amount))
            expected_event_type = HistoryEventType.SPEND
            new_event_type = HistoryEventType.DEPOSIT
            from_chain, to_chain = ChainID.ETHEREUM, ChainID.SCROLL
        elif context.tx_log.topics[0] == FINALIZE_WITHDRAW_ETH:
            raw_amount = decode_abi(['uint256'], context.tx_log.data[:32])[0]
            user_address = hex_or_bytes_to_address(context.tx_log.topics[2])
            amount = from_wei(FVal(raw_amount))
            expected_event_type = HistoryEventType.RECEIVE
            new_event_type = HistoryEventType.WITHDRAWAL
            from_chain, to_chain = ChainID.SCROLL, ChainID.ETHEREUM
        else:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(user_address):
            return DEFAULT_DECODING_OUTPUT

        # Find the corresponding transfer event and update it
        orig_amount = FVal(0)
        bridge_event = self._get_eth_bridge_event(
            context=context,
            expected_event_type=expected_event_type,
            sender=user_address,
        )

        if bridge_event is None:
            return DEFAULT_DECODING_OUTPUT

        orig_amount = bridge_event.balance.amount

        self._edit_eth_bridge_event(
            event=bridge_event,
            new_event_type=new_event_type,
            amount=amount,
            from_chain=from_chain,
            to_chain=to_chain,
        )

        refund_event_idx, refund_amount = self._get_refund_event_index_and_amount(
            decoded_events=context.decoded_events,
            sender=user_address,
        )

        if refund_event_idx is None:
            return DEFAULT_DECODING_OUTPUT

        fee_amount = orig_amount - amount - refund_amount

        spend_l2_fees_event = self._make_l2_fees_event(
            context=context,
            fee_amount=fee_amount,
            sender=user_address,
        )
        context.decoded_events[refund_event_idx] = spend_l2_fees_event

        maybe_reshuffle_events(
            ordered_events=[spend_l2_fees_event, bridge_event],
            events_list=context.decoded_events,
        )

        return DEFAULT_DECODING_OUTPUT

    def _decode_eth_send_message(self, context: DecoderContext) -> DecodingOutput:
        """Decodes an ETH send message event"""
        if context.tx_log.topics[0] != SENT_MESSAGE:
            return DEFAULT_DECODING_OUTPUT

        sender = hex_or_bytes_to_address(context.tx_log.topics[1])
        target = hex_or_bytes_to_address(context.tx_log.topics[2])
        value = hex_or_bytes_to_int(context.tx_log.data[:32])
        amount = from_wei(FVal(value))

        if not self.base.any_tracked([sender, target]):
            return DEFAULT_DECODING_OUTPUT

        bridge_event = self._get_eth_bridge_event(
            context=context,
            expected_event_type=HistoryEventType.SPEND,
            sender=sender,
        )

        if bridge_event is None:
            return DEFAULT_DECODING_OUTPUT

        orig_amount = bridge_event.balance.amount

        self._edit_eth_bridge_event(
            event=bridge_event,
            new_event_type=HistoryEventType.DEPOSIT,
            amount=amount,
            from_chain=ChainID.ETHEREUM,
            to_chain=ChainID.SCROLL,
        )

        refund_event_idx, refund_amount = self._get_refund_event_index_and_amount(
            decoded_events=context.decoded_events,
            sender=sender,
        )

        if refund_event_idx is None:
            return DEFAULT_DECODING_OUTPUT

        fee_amount = orig_amount - amount - refund_amount

        spend_l2_fees_event = self._make_l2_fees_event(
            context=context,
            fee_amount=fee_amount,
            sender=sender,
        )
        context.decoded_events[refund_event_idx] = spend_l2_fees_event

        maybe_reshuffle_events(
            ordered_events=[spend_l2_fees_event, bridge_event],
            events_list=context.decoded_events,
        )

        return DEFAULT_DECODING_OUTPUT

    def _decode_erc20_deposit_withdraw(self, context: DecoderContext) -> DecodingOutput:
        """Decodes ERC20 deposits and withdrawals. (Bridging ERC20 tokens from and to ethereum)"""
        tx_log = context.tx_log

        if tx_log.topics[0] not in (DEPOSIT_ERC20, FINALIZE_WITHDRAW_ERC20):
            return DEFAULT_DECODING_OUTPUT

        from_address = hex_or_bytes_to_address(tx_log.topics[3])
        to_address = hex_or_bytes_to_address(tx_log.data[:32])

        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_DECODING_OUTPUT

        ethereum_token_address = hex_or_bytes_to_address(tx_log.topics[1])
        asset = self.base.get_or_create_evm_token(ethereum_token_address)
        raw_amount = hex_or_bytes_to_int(tx_log.data[32:64])
        amount = asset_normalized_value(raw_amount, asset)

        expected_event_type, new_event_type, from_chain, to_chain, _ = bridge_prepare_data(
            tx_log=tx_log,
            deposit_topics=(DEPOSIT_ERC20,),
            source_chain=ChainID.ETHEREUM,
            target_chain=ChainID.SCROLL,
            from_address=from_address,
            to_address=to_address,
        )

        # Find the fee refund event and remove it
        refund_event_idx, refund_amount = None, FVal(0)
        for idx, event in enumerate(context.decoded_events):
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == from_address and
                event.asset == self.eth and
                event.address == L1_MESSENGER_PROXY
            ):
                refund_event_idx = idx
                refund_amount = event.balance.amount
                break
        if refund_event_idx is not None:
            del context.decoded_events[refund_event_idx]

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.asset == asset and
                event.balance.amount == amount
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
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.asset == self.eth and
                event.address == L1_GATEWAY_ROUTER
            ):
                l2_fees_amount = event.balance.amount - refund_amount
                event.counterparty = CPT_SCROLL
                event.balance.amount = l2_fees_amount
                event.notes = (
                    f'Spend {l2_fees_amount} ETH in L2 fees to bridge ERC20 tokens to Scroll'
                )

        return DEFAULT_DECODING_OUTPUT

    def _get_eth_bridge_event(
            self,
            context: DecoderContext,
            expected_event_type: HistoryEventType,
            sender: str,
    ) -> EvmEvent | None:
        """Finds the eth bridge decoded event given an expected event type"""
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == sender and
                event.asset == self.eth
            ):
                return event
        log.error(
            f'Could not find ETH {expected_event_type} for scroll '
            f'during {context.transaction.tx_hash.hex()}',
        )
        return None

    def _edit_eth_bridge_event(
            self, event: EvmEvent,
            new_event_type: HistoryEventType,
            amount: FVal,
            from_chain: ChainID,
            to_chain: ChainID,
    ) -> EvmEvent:
        """Adjusts the original decoded event to an ETH bridge event"""

        event.event_type = new_event_type
        event.event_subtype = HistoryEventSubType.BRIDGE
        event.counterparty = CPT_SCROLL
        event.balance.amount = amount
        event.notes = (
            f'Bridge {amount} ETH from {from_chain.label()} '
            f'to {to_chain.label()} via Scroll bridge'
        )

        return event

    def _get_refund_event_index_and_amount(
            self,
            decoded_events: list['EvmEvent'],
            sender: str,
    ) -> tuple[int | None, FVal]:
        """Finds the refund event and returns its index and amount
        This event will be replaced by the L2 fees event
        If the event isn't found, returns None and 0
        """
        refund_event_idx, refund_amount = None, FVal(0)
        for idx, event in enumerate(decoded_events):
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == sender and
                event.asset == self.eth and
                event.address == L1_MESSENGER_PROXY
            ):
                refund_event_idx = idx
                refund_amount = event.balance.amount
                break

        return refund_event_idx, refund_amount

    def _make_l2_fees_event(
            self,
            context: DecoderContext,
            fee_amount: FVal,
            sender: str,
    ) -> EvmEvent:
        """Creates a new L2 fees event from the given context and amount"""
        return self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=self.eth,
            balance=Balance(amount=fee_amount),
            location_label=sender,
            notes=f'Spend {fee_amount} ETH on bridging to Scroll (fees on L2)',
            counterparty=CPT_SCROLL,
            address=L1_MESSENGER_PROXY,
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            L1_MESSENGER_PROXY: (self._decode_eth_send_message,),
            L1_ETH_GATEWAY_PROXY: (self._decode_eth_deposit_withdraw,),
            L1_ERC20_GATEWAY: (self._decode_erc20_deposit_withdraw,),
            # USDC uses a custom gateway but implements the same interface
            L1_USDC_GATEWAY: (self._decode_erc20_deposit_withdraw,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (SCROLL_CPT_DETAILS,)
