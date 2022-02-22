from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, ethaddress_to_asset
from rotkehlchen.types import ChecksumEthAddress, EthereumTransaction
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager

KYBER_TRADE_LEGACY = b"\xd3\x0c\xa3\x99\xcbCP~\xce\xc6\xa6)\xa3\\\xf4^\xb9\x8c\xdaU\x0c'im\xcb\r\x8cJ8s\xcel"  # noqa: E501
KYBER_TRADE_LEGACY_UPGRADED = b'\xf7$\xb4\xdff\x17G6\x12\xb5=\x7f\x88\xec\xc6\xea\x980t\xb3\t`\xa0I\xfc\xd0e\x7f\xfe\x80\x80\x83'  # noqa: E501


class KyberDecoder(DecoderInterface):
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum_manager = ethereum_manager
        self.base = base_tools
        self.msg_aggregator = msg_aggregator

    def _decode_legacy_trade(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            decoded_events: List[HistoryBaseEntry],
            upgraded: bool,
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        sender = hex_or_bytes_to_address(tx_log.topics[1])
        source_token_address = hex_or_bytes_to_address(tx_log.data[:32])
        destination_token_address = hex_or_bytes_to_address(tx_log.data[32:64])

        source_token = ethaddress_to_asset(source_token_address)
        if source_token is None:
            return None, None
        destination_token = ethaddress_to_asset(destination_token_address)
        if destination_token is None:
            return None, None

        if upgraded:
            spent_amount_raw = hex_or_bytes_to_int(tx_log.data[96:128])
            return_amount_raw = hex_or_bytes_to_int(tx_log.data[128:160])
        else:
            spent_amount_raw = hex_or_bytes_to_int(tx_log.data[64:96])
            return_amount_raw = hex_or_bytes_to_int(tx_log.data[96:128])

        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_token)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_token)

        for event in decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.location_label == sender and event.asset == source_token and event.balance.amount == spent_amount:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = 'kyber legacy'
                event.notes = f'Swap {event.balance.amount} {event.asset.symbol} in kyber'
            elif event.event_type == HistoryEventType.RECEIVE and event.location_label == sender and event.balance.amount == return_amount and destination_token == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = 'kyber legacy'
                event.notes = f'Receive {event.balance.amount} {event.asset.symbol} from kyber swap'  # noqa: E501

        return None, None

    def decode_action(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] == KYBER_TRADE_LEGACY:
            return self._decode_legacy_trade(tx_log=tx_log, decoded_events=decoded_events, upgraded=False)  # noqa: E501
        if tx_log.topics[0] == KYBER_TRADE_LEGACY_UPGRADED:
            return self._decode_legacy_trade(tx_log=tx_log, decoded_events=decoded_events, upgraded=True)  # noqa: E501
        return None, None

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        return {
            string_to_ethereum_address('0x9ae49C0d7F8F9EF4B864e004FE86Ac8294E20950'): (self.decode_action,),  # noqa: E501
            string_to_ethereum_address('0x9AAb3f75489902f3a48495025729a0AF77d4b11e'): (self.decode_action,),  # noqa: E501
        }
