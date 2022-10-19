import logging
from typing import TYPE_CHECKING, Callable, List, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address

from ..constants import CPT_UNISWAP_V1

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# https://github.com/Uniswap/v1-contracts/blob/c10c08d81d6114f694baa8bd32f555a40f6264da/contracts/uniswap_exchange.vy#L13
TOKEN_PURCHASE = b'\xcd`\xaau\xde\xa3\x07/\xbc\x07\xaem}\x85k]\xc5\xf4\xee\xe8\x88T\xf5\xb4\xab\xf7\xb6\x80\xef\x8b\xc5\x0f'  # noqa: E501
# https://github.com/Uniswap/v1-contracts/blob/c10c08d81d6114f694baa8bd32f555a40f6264da/contracts/uniswap_exchange.vy#L14
ETH_PURCHASE = b'\x7f@\x91\xb4l3\xe9\x18\xa0\xf3\xaaB0vA\xd1{\xb6p)BzSi\xe5K59\x84#\x87\x05'  # noqa: E501


class Uniswapv1Decoder(DecoderInterface):

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def _maybe_decode_swap(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> None:
        """Search for both events. Since the order is not guaranteed try reshuffle in both cases"""
        out_event = in_event = None
        if tx_log.topics[0] == TOKEN_PURCHASE:
            buyer = hex_or_bytes_to_address(tx_log.topics[1])
            # search for a send to buyer from a tracked address
            for event in decoded_events:
                if event.event_type == HistoryEventType.SPEND and event.counterparty == buyer:
                    try:
                        crypto_asset = event.asset.resolve_to_crypto_asset()
                    except (UnknownAsset, WrongAssetType):
                        self.notify_user(event=event, counterparty=CPT_UNISWAP_V1)
                        continue
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.counterparty = CPT_UNISWAP_V1
                    event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in uniswap-v1 from {event.location_label}'  # noqa: E501
                    out_event = event
                elif event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE and event.counterparty == CPT_UNISWAP_V1:  # noqa: :E501
                    in_event = event

        elif tx_log.topics[0] == ETH_PURCHASE:
            buyer = hex_or_bytes_to_address(tx_log.topics[1])
            # search for a receive to buyer
            for event in decoded_events:
                if event.event_type == HistoryEventType.RECEIVE and event.location_label == buyer:
                    try:
                        crypto_asset = event.asset.resolve_to_crypto_asset()
                    except (UnknownAsset, WrongAssetType):
                        self.notify_user(event=event, counterparty=CPT_UNISWAP_V1)
                        continue
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.RECEIVE
                    event.counterparty = CPT_UNISWAP_V1
                    event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} from uniswap-v1 swap in {event.location_label}'  # noqa: E501
                    in_event = event
                elif event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND and event.counterparty == CPT_UNISWAP_V1:  # noqa: :E501
                    out_event = event

        maybe_reshuffle_events(out_event=out_event, in_event=in_event)

    # -- DecoderInterface methods

    def decoding_rules(self) -> List[Callable]:
        return [
            self._maybe_decode_swap,
        ]

    def counterparties(self) -> List[str]:
        return [CPT_UNISWAP_V1]
