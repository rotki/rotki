from typing import TYPE_CHECKING, Callable, List, Optional

from rotkehlchen.accounting.structures import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.typing import EthereumTransaction
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hex_or_bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager

# https://github.com/Uniswap/v1-contracts/blob/c10c08d81d6114f694baa8bd32f555a40f6264da/contracts/uniswap_exchange.vy#L13
TOKEN_PURCHASE = b'\xcd`\xaau\xde\xa3\x07/\xbc\x07\xaem}\x85k]\xc5\xf4\xee\xe8\x88T\xf5\xb4\xab\xf7\xb6\x80\xef\x8b\xc5\x0f'  # noqa: E501
# https://github.com/Uniswap/v1-contracts/blob/c10c08d81d6114f694baa8bd32f555a40f6264da/contracts/uniswap_exchange.vy#L14
ETH_PURCHASE = b'\x7f@\x91\xb4l3\xe9\x18\xa0\xf3\xaaB0vA\xd1{\xb6p)BzSi\xe5K59\x84#\x87\x05'  # noqa: E501


class Uniswapv1Decoder(DecoderInterface):
    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum_manager = ethereum_manager
        self.base = base_tools
        self.msg_aggregator = msg_aggregator

    def _maybe_decode_swap(  # pylint: disable=no-self-use
            self,
            token: Optional[EthereumToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Optional[HistoryBaseEntry]:
        if tx_log.topics[0] == TOKEN_PURCHASE:
            buyer = hex_or_bytes_to_address(tx_log.topics[1])
            # search for a send to buyer from a tracked address
            for event in decoded_events:
                if event.event_type == HistoryEventType.SPEND and event.counterparty == buyer:
                    event.event_type = HistoryEventType.SWAP
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.counterparty = 'uniswap-v1'
                    event.notes = f'Swap {event.balance.amount} {event.asset.symbol} in uniswap-v1 from {event.location_label}'  # noqa: E501
                    return None

        elif tx_log.topics[0] == ETH_PURCHASE:
            buyer = hex_or_bytes_to_address(tx_log.topics[1])
            # search for a receive to buyer
            for event in decoded_events:
                if event.event_type == HistoryEventType.RECEIVE and event.location_label == buyer:
                    event.event_type = HistoryEventType.SWAP
                    event.event_subtype = HistoryEventSubType.RECEIVE
                    event.counterparty = 'uniswap-v1'
                    event.notes = f'Receive {event.balance.amount} {event.asset.symbol} from uniswap-v1 swap in {event.location_label}'  # noqa: E501
                    return None

        return None

    def decoding_rules(self) -> List[Callable]:
        return [
            self._maybe_decode_swap,
        ]
