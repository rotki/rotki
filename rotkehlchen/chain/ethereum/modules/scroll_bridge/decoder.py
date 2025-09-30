import logging
from typing import TYPE_CHECKING, Any, Final

from eth_abi import decode as decode_abi

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import (
    bridge_match_transfer,
    bridge_prepare_data,
    maybe_reshuffle_events,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.scroll.constants import CPT_SCROLL, SCROLL_CPT_DETAILS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# https://docs.scroll.io/en/developers/scroll-contracts/
L1_GATEWAY_ROUTER: Final = string_to_evm_address('0xF8B1378579659D8F7EE5f3C929c2f3E332E41Fd6')
L1_ETH_GATEWAY_PROXY: Final = string_to_evm_address('0x7F2b8C31F88B6006c382775eea88297Ec1e3E905')
L1_ERC20_GATEWAY: Final = string_to_evm_address('0xD8A791fE2bE73eb6E6cF1eb0cb3F36adC9B3F8f9')
L1_USDC_GATEWAY: Final = string_to_evm_address('0xf1AF3b23DE0A5Ca3CAb7261cb0061C0D779A5c7B')
L1_MESSENGER_PROXY: Final = string_to_evm_address('0x6774Bcbd5ceCeF1336b5300fb5186a12DDD8b367')

DEPOSIT_ETH: Final = b'fp\xde\x85n\xc8\xbf\\\xb2\xb7\xe9W\xc5\xdc$u\x97\x16\x05oy\xd9~\xa5\xe7\xc99\xca\x0b\xa5\xa6u'  # noqa: E501
FINALIZE_WITHDRAW_ETH: Final = b'\x96\xdb]\x1c\xee\x1d\xd2v\x08&\xbbV\xfa\xbd\x9c\x9fn\x97\x80\x83\xe0\xa8\xb8\x85Y\xc7A\xa2\x9e\x97F\xe7'  # noqa: E501
SENT_MESSAGE: Final = b'\x10Cq\xf3\xb4B\x86\x1a*{\x82\xa0p\xaf\xbb\xaa\xb7H\xbb\x13u{\xf4wi\xe1p\xe3x\t\xec\x1e'  # noqa: E501
DEPOSIT_ERC20: Final = b'1\xcd;\x97nMe@"\xbf\x95\xc6\x8a,\xe5?\x1d]\x94\xaf\xab\xe0EM(2 \x8e\xeb@\xaf%'  # noqa: E501
FINALIZE_WITHDRAW_ERC20: Final = b'\xc6\xf9\x85\x87;7\x80W\x05\xf6\xbc\xe7V\xdc\xe3\xd1\xffK`>)\x8dPb\x88\xcc\xe4\x99\x92hF\xa7'  # noqa: E501


class ScrollBridgeDecoder(EvmDecoderInterface):
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

    def _decode_eth_deposit_withdraw(self, context: DecoderContext) -> DecodingOutput:
        """Decodes ETH deposit and withdraw events. (Bridging ETH from and to ethereum)"""
        if context.tx_log.topics[0] == DEPOSIT_ETH:
            raw_amount = decode_abi(['uint256'], context.tx_log.data)[0]
            user_address = bytes_to_address(context.tx_log.topics[1])
            amount = from_wei(FVal(raw_amount))
            expected_event_type = HistoryEventType.SPEND
            new_event_type = HistoryEventType.DEPOSIT
            from_chain, to_chain = ChainID.ETHEREUM, ChainID.SCROLL
        elif context.tx_log.topics[0] == FINALIZE_WITHDRAW_ETH:
            raw_amount = decode_abi(['uint256'], context.tx_log.data[:32])[0]
            user_address = bytes_to_address(context.tx_log.topics[2])
            amount = from_wei(FVal(raw_amount))
            expected_event_type = HistoryEventType.RECEIVE
            new_event_type = HistoryEventType.WITHDRAWAL
            from_chain, to_chain = ChainID.SCROLL, ChainID.ETHEREUM
        else:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(user_address):
            return DEFAULT_DECODING_OUTPUT

        return self._decode_eth_events(
            context=context,
            expected_event_type=expected_event_type,
            new_event_type=new_event_type,
            from_chain=from_chain,
            to_chain=to_chain,
            amount=amount,
            user_address=user_address,
        )

    def _decode_eth_send_message(self, context: DecoderContext) -> DecodingOutput:
        """Decodes an ETH send message event"""
        if context.tx_log.topics[0] != SENT_MESSAGE:
            return DEFAULT_DECODING_OUTPUT

        sender = bytes_to_address(context.tx_log.topics[1])
        target = bytes_to_address(context.tx_log.topics[2])
        value = int.from_bytes(context.tx_log.data[:32])
        amount = from_wei(FVal(value))

        if not self.base.any_tracked([sender, target]):
            return DEFAULT_DECODING_OUTPUT

        return self._decode_eth_events(
            context=context,
            expected_event_type=HistoryEventType.SPEND,
            new_event_type=HistoryEventType.DEPOSIT,
            from_chain=ChainID.ETHEREUM,
            to_chain=ChainID.SCROLL,
            amount=amount,
            user_address=sender,
        )

    def _decode_erc20_deposit_withdraw(self, context: DecoderContext) -> DecodingOutput:
        """Decodes ERC20 deposits and withdrawals. (Bridging ERC20 tokens from and to ethereum)"""
        if (tx_log := context.tx_log).topics[0] not in (DEPOSIT_ERC20, FINALIZE_WITHDRAW_ERC20):
            return DEFAULT_DECODING_OUTPUT

        from_address = bytes_to_address(tx_log.topics[3])
        to_address = bytes_to_address(tx_log.data[:32])
        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_DECODING_OUTPUT

        ethereum_token_address = bytes_to_address(tx_log.topics[1])
        asset = self.base.get_or_create_evm_token(ethereum_token_address)
        raw_amount = int.from_bytes(tx_log.data[32:64])
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
        # We are only interested in how much the user spent as a fee,
        # so we are subtracting the refund amount from the fee event
        refund_event_idx, refund_amount = None, ZERO
        for idx, event in enumerate(context.decoded_events):
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == from_address and
                event.asset == A_ETH and
                event.address == L1_MESSENGER_PROXY
            ):
                refund_event_idx = idx
                refund_amount = event.amount
                break
        if refund_event_idx is not None:
            del context.decoded_events[refund_event_idx]

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
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
                    counterparty=SCROLL_CPT_DETAILS,
                )
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.asset == A_ETH and
                event.address == L1_GATEWAY_ROUTER
            ):  # Update the fee event by subtracting the refund amount
                l2_fees_amount = event.amount - refund_amount
                event.counterparty = CPT_SCROLL
                event.amount = l2_fees_amount
                event.notes = f'Spend {l2_fees_amount} ETH in L2 fees to bridge ERC20 tokens to Scroll'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_eth_events(
            self,
            context: DecoderContext,
            expected_event_type: HistoryEventType,
            new_event_type: HistoryEventType,
            from_chain: ChainID,
            to_chain: ChainID,
            amount: FVal,
            user_address: str,
    ) -> DecodingOutput:
        """Updates the ETH bridge events given the event details"""
        # Find the corresponding transfer event and update it
        if (bridge_event := self._get_eth_bridge_event(
            context=context,
            expected_event_type=expected_event_type,
            sender=user_address,
        )) is None:
            return DEFAULT_DECODING_OUTPUT

        # The original amount will be edited on the event, keeping a copy here
        orig_amount = bridge_event.amount

        # Edit the main bridge event
        bridge_event.event_type = new_event_type
        bridge_event.event_subtype = HistoryEventSubType.BRIDGE
        bridge_event.counterparty = CPT_SCROLL
        bridge_event.amount = amount
        bridge_event.notes = (
            f'Bridge {amount} ETH from {from_chain.label()} '
            f'to {to_chain.label()} via Scroll bridge'
        )

        # Edit the fee events: remove the refund event and add the L2 fees event
        refund_event_idx, refund_amount = self._get_refund_event_index_and_amount(
            decoded_events=context.decoded_events,
            sender=user_address,
        )
        if (fee_amount := orig_amount - amount - refund_amount) > ZERO:
            spend_l2_fees_event = self._make_l2_fees_event(
                context=context,
                fee_amount=fee_amount,
                sender=user_address,
            )
            if refund_event_idx is not None:  # Replace the refund event if found
                context.decoded_events[refund_event_idx] = spend_l2_fees_event
            else:
                context.decoded_events.append(spend_l2_fees_event)
            maybe_reshuffle_events(
                ordered_events=[spend_l2_fees_event, bridge_event],
                events_list=context.decoded_events,
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
                event.asset == A_ETH
            ):
                return event
        log.error(
            f'Could not find ETH {expected_event_type} for scroll '
            f'during {context.transaction.tx_hash.hex()}',
        )
        return None

    def _get_refund_event_index_and_amount(
            self,
            decoded_events: list['EvmEvent'],
            sender: str,
    ) -> tuple[int | None, FVal]:
        """Finds the refund event and returns its index and amount
        This event will be replaced by the L2 fees event.
        If the event isn't found, returns None and 0
        """
        refund_event_idx, refund_amount = None, ZERO
        for idx, event in enumerate(decoded_events):
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == sender and
                event.asset == A_ETH and
                event.address == L1_MESSENGER_PROXY
            ):
                refund_event_idx = idx
                refund_amount = event.amount
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
            asset=A_ETH,
            amount=fee_amount,
            location_label=sender,
            notes=f'Spend {fee_amount} ETH as a fee for bridging to Scroll',
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
